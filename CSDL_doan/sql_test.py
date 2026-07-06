import pyodbc
import time

print("=" * 60)
print("🔍 KIỂM TRA KẾT NỐI SQL SERVER")
print("=" * 60)

# Đợi SQL restart hoàn tất
time.sleep(3)

# Các cách kết nối
servers = ["localhost", "127.0.0.1", ".", "(local)"]

for server in servers:
    try:
        conn_str = f"DRIVER={{SQL Server}};SERVER={server};DATABASE=master;Trusted_Connection=yes;"
        print(f"\n🔄 Thử kết nối với: {server}")
        conn = pyodbc.connect(conn_str, timeout=5)
        print(f"   ✅ THÀNH CÔNG! 🎉")

        cursor = conn.cursor()
        cursor.execute("SELECT @@SERVERNAME, DB_NAME(), GETDATE()")
        row = cursor.fetchone()
        print(f"\n📌 Thông tin SQL Server:")
        print(f"   - Server: {row[0]}")
        print(f"   - Database hiện tại: {row[1]}")
        print(f"   - Thời gian: {row[2]}")

        conn.close()
        print("\n" + "=" * 60)
        print(f"🎉 KẾT NỐI SQL SERVER THÀNH CÔNG!")
        print(f"   Server: {server}")
        print("=" * 60)
        break

    except Exception as e:
        print(f"   ❌ Lỗi: {str(e)[:60]}")

print("\n✅ Đã kiểm tra xong!")