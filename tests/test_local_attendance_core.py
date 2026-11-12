import sys
import sqlite3
import tempfile
import unittest
from pathlib import Path

import numpy as np
from cryptography.fernet import Fernet

sys.path.insert(
    0, str(Path(__file__).resolve().parents[1] / "Face-ID-Frontend")
)

from local_attendance_core import (  # pyright: ignore[reportMissingImports]
    MODEL_VERSION,
    CachedStudent,
    CachedSession,
    ExtractedFace,
    LocalAttendanceCore,
    LocalAttendanceStore,
)


class FakeExtractor:
    def __init__(self, faces):
        self.faces = faces
        self.last_image_shape = None

    def extract(self, image):
        self.last_image_shape = image.shape
        return self.faces


class LocalAttendanceCoreTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "attendance.sqlite3"
        self.key = Fernet.generate_key()
        self.store = LocalAttendanceStore(self.database_path, self.key)
        self.student_vector = np.zeros(512, dtype=np.float32)
        self.student_vector[0] = 1.0
        self.store.replace_student_cache(
            [
                CachedStudent(
                    sinh_vien_id="student-1",
                    ma_sv="SV001",
                    ho_ten="Nguyen Van A",
                    embedding=self.student_vector,
                    vector_version=MODEL_VERSION,
                )
            ]
        )
        self.store.replace_session_cache(
            [CachedSession("12", "class-1", "2026-11-12", "08:00")]
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_match_records_one_pending_attendance(self):
        core = LocalAttendanceCore(
            self.store,
            FakeExtractor(
                [ExtractedFace(self.student_vector, [1, 2, 30, 40], 0.99)]
            ),
        )

        result = core.process_frame(12, np.zeros((48, 48, 3), dtype=np.uint8))

        self.assertEqual(result["ket_qua"][0]["ket_qua"], "thanh_cong")
        self.assertEqual(result["ket_qua"][0]["ma_sv"], "SV001")
        pending = self.store.get_pending_attendance()
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]["ca_hoc_id"], "12")
        self.assertEqual(pending[0]["trang_thai"], "co_mat")

    def test_duplicate_match_does_not_create_second_attendance(self):
        core = LocalAttendanceCore(
            self.store,
            FakeExtractor(
                [ExtractedFace(self.student_vector, [1, 2, 30, 40], 0.99)]
            ),
        )

        first = core.process_frame(12, np.zeros((48, 48, 3)))
        second = core.process_frame(12, np.zeros((48, 48, 3)))

        self.assertEqual(first["ket_qua"][0]["ket_qua"], "thanh_cong")
        self.assertEqual(second["ket_qua"][0]["ket_qua"], "da_diem_danh_roi")
        self.assertEqual(len(self.store.get_pending_attendance()), 1)

    def test_stranger_is_not_recorded(self):
        stranger_vector = np.zeros(512, dtype=np.float32)
        stranger_vector[1] = 1.0
        core = LocalAttendanceCore(
            self.store,
            FakeExtractor(
                [ExtractedFace(stranger_vector, [1, 2, 30, 40], 0.99)]
            ),
        )

        result = core.process_frame(12, np.zeros((48, 48, 3)))

        self.assertEqual(result["ket_qua"][0]["ket_qua"], "khong_du_giong")
        self.assertFalse(result["ket_qua"][0]["nhan_dien"])
        self.assertEqual(self.store.get_pending_attendance(), [])

    def test_incompatible_vector_version_is_rejected_without_clearing_cache(self):
        with self.assertRaises(ValueError):
            self.store.replace_student_cache(
                [
                    CachedStudent(
                        sinh_vien_id="student-2",
                        ma_sv="SV002",
                        ho_ten="Nguyen Van B",
                        embedding=self.student_vector,
                        vector_version="different-model",
                    )
                ]
            )

        self.assertEqual(
            [student.ma_sv for student in self.store.get_cached_students()],
            ["SV001"],
        )

    def test_uncached_session_is_rejected(self):
        core = LocalAttendanceCore(
            self.store,
            FakeExtractor(
                [ExtractedFace(self.student_vector, [1, 2, 30, 40], 0.99)]
            ),
        )

        with self.assertRaisesRegex(ValueError, "chưa được cache"):
            core.process_frame(99, np.zeros((48, 48, 3)))

        self.assertEqual(self.store.get_pending_attendance(), [])

    def test_existing_cache_with_old_version_is_rejected(self):
        connection = sqlite3.connect(self.database_path)
        try:
            connection.execute(
                "UPDATE cached_students SET vector_version = ?",
                ("old-model-version",),
            )
            connection.commit()
        finally:
            connection.close()

        with self.assertRaisesRegex(ValueError, "không tương thích"):
            self.store.get_cached_students()


if __name__ == "__main__":
    unittest.main()
