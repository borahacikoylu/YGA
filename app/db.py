import mysql.connector


def get_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="02122002",
        database="django",
    )


def insert_concert(konser_adi, sehir_id, adres, tarih, saat, fiyat, mekan, image):
    try:
        conn = get_connection()
        cursor = conn.cursor()

        sql = """
        INSERT INTO concerts (konser_adi, sehir_id, adres, tarih, saat, fiyat, mekan, image)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """

        cursor.execute(
            sql, (konser_adi, sehir_id, adres, tarih, saat, fiyat, mekan, image)
        )
        conn.commit()
        print(f"✅ '{konser_adi}' veritabanına eklendi.")

    except Exception as e:
        print(f"❌ Hata oluştu: {e}")

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
