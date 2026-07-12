import pyodbc
import config

try:
    # Kết nối thử bằng thông tin trong file config.py của bạn
    conn_str = f"DRIVER={{SQL Server}};SERVER={config.DB_SERVER};DATABASE={config.DB_NAME};Trusted_Connection=yes;"
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()

    # Chạy thử một lệnh quét xem database có bảng nào không
    cursor.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'BASE TABLE'")
    tables = cursor.fetchall()

    print("=========================================")
    print("🎉 CHÚC MỪNG VIỆT ANH! KẾT NỐI THÀNH CÔNG RỒI!")
    print(f"Đã tìm thấy {len(tables)} bảng dữ liệu trong Database QLCX.")
    print("=========================================")

    cursor.close()
    conn.close()

except Exception as e:
    print("=========================================")
    print("❌ KẾT NỐI THẤT BẠI RỒI BẠN ƠI!")
    print("Lỗi chi tiết:", e)
    print("=========================================")