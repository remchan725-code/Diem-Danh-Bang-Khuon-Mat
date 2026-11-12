import os
import sqlite3
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator, Protocol, Sequence

import numpy as np
from cryptography.fernet import Fernet


MODEL_NAME = "buffalo_l"
MODEL_VERSION = "insightface_buffalo_l_v1"
VECTOR_DIMENSION = 512
DEFAULT_COSINE_DISTANCE_THRESHOLD = 0.4


@dataclass(frozen=True)
class ExtractedFace:
    embedding: np.ndarray
    bbox: list[int]
    confidence: float


@dataclass(frozen=True)
class CachedStudent:
    sinh_vien_id: str
    ma_sv: str
    ho_ten: str
    embedding: Sequence[float] | np.ndarray
    vector_version: str


@dataclass(frozen=True)
class CachedSession:
    ca_hoc_id: str
    lop_id: str
    ngay: str
    gio_bat_dau: str
    gio_ket_thuc: str | None = None


class FaceExtractor(Protocol):
    def extract(self, image: np.ndarray) -> list[ExtractedFace]:
        ...


def default_database_path() -> Path:
    app_data = os.getenv("LOCALAPPDATA")
    base_path = Path(app_data) if app_data else Path.home() / ".local" / "share"
    return base_path / "DiemDanhBangKhuonMat" / "attendance.sqlite3"


def _validated_embedding(embedding: Sequence[float] | np.ndarray) -> np.ndarray:
    vector = np.asarray(embedding, dtype=np.float32)
    if vector.shape != (VECTOR_DIMENSION,):
        raise ValueError(f"Embedding phải có đúng {VECTOR_DIMENSION} chiều.")
    if not np.all(np.isfinite(vector)):
        raise ValueError("Embedding chứa giá trị không hợp lệ.")

    norm = float(np.linalg.norm(vector))
    if norm == 0:
        raise ValueError("Embedding không được là vector zero.")
    return vector / norm


class InsightFaceExtractor:
    def __init__(self) -> None:
        from insightface.app import FaceAnalysis
        import onnxruntime

        available = onnxruntime.get_available_providers()
        providers = [
            provider
            for provider in ("CUDAExecutionProvider", "CPUExecutionProvider")
            if provider in available
        ]
        if not providers:
            raise RuntimeError("Không tìm thấy ONNX Runtime provider phù hợp.")

        self._use_cuda = providers[0] == "CUDAExecutionProvider"
        self._app = FaceAnalysis(name=MODEL_NAME, providers=providers)
        self._app.prepare(ctx_id=0 if self._use_cuda else -1, det_size=(640, 640))

    def extract(self, image: np.ndarray) -> list[ExtractedFace]:
        if not isinstance(image, np.ndarray) or image.ndim != 3:
            raise ValueError("Frame phải là ảnh màu dạng NumPy array.")

        results = []
        for face in self._app.get(image):
            results.append(
                ExtractedFace(
                    embedding=np.asarray(face.embedding, dtype=np.float32),
                    bbox=np.asarray(face.bbox, dtype=np.int32).tolist(),
                    confidence=float(face.det_score),
                )
            )
        return results


class LocalAttendanceStore:
    def __init__(
        self,
        database_path: str | Path | None = None,
        encryption_key: bytes | str | None = None,
    ) -> None:
        key = encryption_key or os.getenv("LOCAL_FERNET_KEY")
        if not key:
            raise RuntimeError(
                "Cần cấu hình LOCAL_FERNET_KEY để mã hóa vector cache trên thiết bị."
            )
        if isinstance(key, str):
            key = key.encode("ascii")

        self._fernet = Fernet(key)
        self.database_path = Path(database_path or default_database_path())
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @contextmanager
    def _connect(self) -> Generator[sqlite3.Connection, None, None]:
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS cached_students (
                    sinh_vien_id TEXT PRIMARY KEY,
                    ma_sv TEXT NOT NULL,
                    ho_ten TEXT NOT NULL,
                    embedding_encrypted BLOB NOT NULL,
                    vector_version TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS cached_sessions (
                    ca_hoc_id TEXT PRIMARY KEY,
                    lop_id TEXT NOT NULL,
                    ngay TEXT NOT NULL,
                    gio_bat_dau TEXT NOT NULL,
                    gio_ket_thuc TEXT
                );

                CREATE TABLE IF NOT EXISTS local_attendance (
                    id INTEGER PRIMARY KEY,
                    request_id TEXT NOT NULL UNIQUE,
                    ca_hoc_id TEXT NOT NULL,
                    sinh_vien_id TEXT NOT NULL,
                    thoi_gian TEXT NOT NULL,
                    trang_thai TEXT NOT NULL CHECK (trang_thai = 'co_mat'),
                    sync_status TEXT NOT NULL DEFAULT 'pending'
                        CHECK (sync_status IN ('pending', 'synced')),
                    UNIQUE (ca_hoc_id, sinh_vien_id)
                );
                """
            )

    def replace_student_cache(self, students: Sequence[CachedStudent]) -> None:
        prepared = []
        student_ids = set()
        updated_at = datetime.now(timezone.utc).isoformat()

        for student in students:
            if student.sinh_vien_id in student_ids:
                raise ValueError(f"Trùng sinh_vien_id trong cache: {student.sinh_vien_id}")
            if student.vector_version != MODEL_VERSION:
                raise ValueError(
                    f"Vector của {student.ma_sv} không tương thích "
                    f"(cần {MODEL_VERSION}, nhận {student.vector_version})."
                )
            vector = _validated_embedding(student.embedding)
            student_ids.add(student.sinh_vien_id)
            prepared.append(
                (
                    student.sinh_vien_id,
                    student.ma_sv,
                    student.ho_ten,
                    self._fernet.encrypt(vector.tobytes()),
                    student.vector_version,
                    updated_at,
                )
            )

        with self._connect() as connection:
            connection.execute("DELETE FROM cached_students")
            connection.executemany(
                """
                INSERT INTO cached_students
                    (sinh_vien_id, ma_sv, ho_ten, embedding_encrypted,
                     vector_version, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                prepared,
            )

    def get_cached_students(self) -> list[CachedStudent]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT sinh_vien_id, ma_sv, ho_ten, embedding_encrypted, vector_version
                FROM cached_students
                ORDER BY ma_sv
                """
            ).fetchall()

        students = []
        for row in rows:
            if row["vector_version"] != MODEL_VERSION:
                raise ValueError(
                    f"Cache của {row['ma_sv']} không tương thích "
                    f"(cần {MODEL_VERSION}, nhận {row['vector_version']})."
                )
            raw_embedding = self._fernet.decrypt(bytes(row["embedding_encrypted"]))
            embedding = np.frombuffer(raw_embedding, dtype=np.float32).copy()
            students.append(
                CachedStudent(
                    sinh_vien_id=row["sinh_vien_id"],
                    ma_sv=row["ma_sv"],
                    ho_ten=row["ho_ten"],
                    embedding=embedding,
                    vector_version=row["vector_version"],
                )
            )
        return students

    def replace_session_cache(self, sessions: Sequence[CachedSession]) -> None:
        prepared = [
            (
                session.ca_hoc_id,
                session.lop_id,
                session.ngay,
                session.gio_bat_dau,
                session.gio_ket_thuc,
            )
            for session in sessions
        ]
        if len({item[0] for item in prepared}) != len(prepared):
            raise ValueError("Danh sách ca học cache có ca_hoc_id bị trùng.")

        with self._connect() as connection:
            connection.execute("DELETE FROM cached_sessions")
            connection.executemany(
                """
                INSERT INTO cached_sessions
                    (ca_hoc_id, lop_id, ngay, gio_bat_dau, gio_ket_thuc)
                VALUES (?, ?, ?, ?, ?)
                """,
                prepared,
            )

    def get_cached_sessions(self) -> list[dict]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT ca_hoc_id, lop_id, ngay, gio_bat_dau, gio_ket_thuc
                FROM cached_sessions
                ORDER BY ngay DESC, gio_bat_dau DESC
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def has_cached_session(self, ca_hoc_id: str) -> bool:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT 1 FROM cached_sessions WHERE ca_hoc_id = ?",
                (ca_hoc_id,),
            ).fetchone()
        return row is not None

    def record_attendance(self, ca_hoc_id: str, sinh_vien_id: str) -> bool:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO local_attendance
                    (request_id, ca_hoc_id, sinh_vien_id, thoi_gian, trang_thai)
                VALUES (?, ?, ?, ?, 'co_mat')
                ON CONFLICT (ca_hoc_id, sinh_vien_id) DO NOTHING
                """,
                (
                    str(uuid.uuid4()),
                    ca_hoc_id,
                    sinh_vien_id,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
        return cursor.rowcount == 1

    def get_attendance(self, ca_hoc_id: str) -> list[dict]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT a.request_id, a.ca_hoc_id, a.sinh_vien_id, a.thoi_gian,
                       a.trang_thai, a.sync_status, s.ma_sv, s.ho_ten
                FROM local_attendance a
                LEFT JOIN cached_students s ON s.sinh_vien_id = a.sinh_vien_id
                WHERE a.ca_hoc_id = ?
                ORDER BY a.thoi_gian
                """,
                (ca_hoc_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_pending_attendance(self) -> list[dict]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT request_id, ca_hoc_id, sinh_vien_id, thoi_gian, trang_thai
                FROM local_attendance
                WHERE sync_status = 'pending'
                ORDER BY thoi_gian
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def mark_attendance_synced(self, request_ids: Sequence[str]) -> None:
        if not request_ids:
            return
        placeholders = ",".join("?" for _ in request_ids)
        with self._connect() as connection:
            connection.execute(
                f"""
                UPDATE local_attendance
                SET sync_status = 'synced'
                WHERE request_id IN ({placeholders})
                """,
                list(request_ids),
            )


class LocalAttendanceCore:
    def __init__(
        self,
        store: LocalAttendanceStore,
        extractor: FaceExtractor | None = None,
        distance_threshold: float = DEFAULT_COSINE_DISTANCE_THRESHOLD,
    ) -> None:
        if not 0 <= distance_threshold <= 2:
            raise ValueError("Ngưỡng cosine distance phải nằm trong khoảng 0..2.")
        self.store = store
        self._extractor = extractor
        self.distance_threshold = distance_threshold
        self._students: list[CachedStudent] = []
        self.reload_student_cache()

    def reload_student_cache(self) -> None:
        self._students = self.store.get_cached_students()

    def _get_extractor(self) -> FaceExtractor:
        if self._extractor is None:
            self._extractor = InsightFaceExtractor()
        return self._extractor

    def process_frame(self, ca_hoc_id: str | int, image: np.ndarray) -> dict:
        session_id = str(ca_hoc_id)
        if not self.store.has_cached_session(session_id):
            raise ValueError(f"Ca học {session_id} chưa được cache trên thiết bị.")

        faces = self._get_extractor().extract(image)
        results = []

        for face in faces:
            embedding = _validated_embedding(face.embedding)
            result = {
                "nhan_dien": False,
                "ket_qua": "khong_tim_thay_ung_vien",
                "khoang_cach": None,
                "bbox": face.bbox,
            }

            if self._students:
                distances = [
                    max(
                        0.0,
                        min(
                            2.0,
                            1.0 - float(np.dot(embedding, _validated_embedding(student.embedding))),
                        ),
                    )
                    for student in self._students
                ]
                best_index = int(np.argmin(distances))
                distance = distances[best_index]
                student = self._students[best_index]
                result["khoang_cach"] = round(distance, 4)

                if distance <= self.distance_threshold:
                    was_recorded = self.store.record_attendance(
                        session_id, student.sinh_vien_id
                    )
                    result.update(
                        {
                            "nhan_dien": True,
                            "ket_qua": "thanh_cong" if was_recorded else "da_diem_danh_roi",
                            "sinh_vien_id": student.sinh_vien_id,
                            "ma_sv": student.ma_sv,
                            "ho_ten": student.ho_ten,
                        }
                    )
                else:
                    result["ket_qua"] = "khong_du_giong"

            results.append(result)

        return {"so_mat_thay": len(faces), "ket_qua": results}
