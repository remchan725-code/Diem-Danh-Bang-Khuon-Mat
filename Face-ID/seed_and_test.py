#tai psycopg2-binary truoc khi chay cu nhe
import psycopg2
import os

DB_CONFIG = {
    "host" : os.getenv("DB_HOST","localhost"),
    "dbname": os.getenv("DB_NAME","attendance_db"),
    "user" : os.getenv("DB_USER","postgres"),
    "password":os.getenv("DB_PASSWORD","12341234"),#mk that la 12341234
    "port": os.getenv("DB_PORT","5432")
}
SCHEMA_PATH = r"C:\CloneGitHub\Diem-Danh-Bang-Khuon-Mat\Face-ID\schema.sql"

def reset_and_create_schema(conn) -> None:
    cur = conn.cursor()
    cur.execute("""
    DROP TABLE IF EXISTS LopHoc CASCADE;
    DROP TABLE IF EXISTS LichSuDiemDanh CASCADE;
    DROP TABLE IF EXISTS CaHoc CASCADE;
    DROP TABLE IF EXISTS SinhVien CASCADE;
""") #gửi lệnh "DROP..." lên SQL
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        cur.execute(f.read())
        conn.commit()
        cur.close()

def seed_data(conn) -> None:
    cur = conn.cursor()
    cur.execute("INSERT INTO LopHoc (ten_lop) VALUES (%s) RETURNING id",("CNTT01",))
    lop_id = cur.fetchone()[0]
    
    sinh_viens = [
        ("250174802010022","Nguyễn Minh Đức"),
        ("250174802010025","Nguyễn Hồng Nam"),
        ("250174802010047","Phùng Thanh Độ"),
    ]
    sv_ids = []
    for ma_sv,ho_ten in sinh_viens:
        cur.execute("INSERT INTO SinhVien(ma_sv,ho_ten,lop_id) VALUES (%s,%s,%s) RETURNING id",
        (ma_sv,ho_ten,lop_id)
        )
        sv_ids.append(cur.fetchone()[0])
        cur.execute("INSERT INTO CaHoc(lop_id,ngay,gio_bat_dau) VALUES (%s,%s,%s) RETURNING id",
        (lop_id, "2026-09-08", "07:30"),
    )
    ca_hoc_id = cur.fetchone()[0]
 
    trang_thais = ["co_mat", "tre", "vang"]
    for sv_id, trang_thai in zip(sv_ids, trang_thais):
        cur.execute(
            "INSERT INTO LichSuDiemDanh (sinh_vien_id, ca_hoc_id, trang_thai) VALUES (%s, %s, %s)",
            (sv_id, ca_hoc_id, trang_thai),
        )
 
    conn.commit()
    cur.close()
    print(f"Đã thêm 1 lớp, {len(sinh_viens)} sinh viên, 1 ca học, {len(sinh_viens)} bản ghi điểm danh.")
 
 
def test_join_query(conn) -> None:
    print("\n--- Kết quả JOIN: họ tên - trạng thái điểm danh ---")
    cur = conn.cursor()
    cur.execute("""
        SELECT SinhVien.ho_ten, LichSuDiemDanh.trang_thai
        FROM LichSuDiemDanh
        JOIN SinhVien ON LichSuDiemDanh.sinh_vien_id = SinhVien.id
    """)
    for ho_ten, trang_thai in cur.fetchall():
        print(f"  {ho_ten:20s} -> {trang_thai}")
    cur.close()
 
 
if __name__ == "__main__":
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        reset_and_create_schema(conn)
        seed_data(conn)
        test_join_query(conn)
        print(f"\nHoàn tất. Đã chạy trên PostgreSQL database: {DB_CONFIG['dbname']}")
    finally:
        conn.close()
        