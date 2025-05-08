from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import mysql.connector
from datetime import datetime

app = FastAPI(title="Bilet Satış API")

# CORS ayarları
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Veritabanı bağlantısı
def get_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="02122002",
        database="django",
    )

# Pydantic modelleri
class UserCreate(BaseModel):
    isim: str
    soyisim: str
    mail: str
    yas: int
    password: str

class UserLogin(BaseModel):
    mail: str
    password: str

class TicketCreate(BaseModel):
    concert_id: int

class Concert(BaseModel):
    konser_adi: str
    tarih: datetime
    saat: str
    fiyat: float
    mekan: str
    adres: str

class UserProfile(BaseModel):
    isim: str
    soyisim: str
    mail: str
    yas: int
    bakiye: float
    biletler: List[Concert]

# API Endpoint'leri
@app.post("/register/")
async def register_user(user: UserCreate):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Kullanıcı kontrolü
        cursor.execute("SELECT * FROM users WHERE mail = %s", (user.mail,))
        if cursor.fetchone():
            raise HTTPException(status_code=409, detail="Bu mail ile zaten kayıtlı kullanıcı var.")
        
        # Yeni kullanıcı ekle
        cursor.execute(
            """
            INSERT INTO users (isim, soyisim, mail, yas, password, bakiye)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (user.isim, user.soyisim, user.mail, user.yas, user.password, 1000)
        )
        conn.commit()
        return {"message": "Kayıt başarılı"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        cursor.close()
        conn.close()

@app.post("/login/")
async def login_user(user: UserLogin):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute(
            "SELECT * FROM users WHERE mail = %s AND password = %s",
            (user.mail, user.password)
        )
        user_data = cursor.fetchone()
        
        if user_data:
            return {
                "message": "Giriş başarılı",
                "isim": user_data["isim"],
                "soyisim": user_data["soyisim"],
                "bakiye": user_data["bakiye"]
            }
        else:
            raise HTTPException(status_code=401, detail="Geçersiz mail veya şifre.")
    
    finally:
        cursor.close()
        conn.close()

@app.get("/profile/{user_id}")
async def user_profile(user_id: int):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Kullanıcı bilgisi
        cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı")
        
        # Bilet bilgileri
        cursor.execute(
            """
            SELECT c.konser_adi, c.tarih, c.saat, c.fiyat, c.mekan, c.adres
            FROM tickets t
            JOIN concerts c ON t.concert = c.concert_id
            WHERE t.buyer = %s
            """,
            (user_id,)
        )
        biletler = cursor.fetchall()
        
        return {
            "isim": user["isim"],
            "soyisim": user["soyisim"],
            "mail": user["mail"],
            "yas": user["yas"],
            "bakiye": user["bakiye"],
            "biletler": biletler
        }
    
    finally:
        cursor.close()
        conn.close()

@app.post("/buy-ticket/")
async def buy_ticket(ticket: TicketCreate, user_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Konser kontrolü
        cursor.execute("SELECT * FROM concerts WHERE concert_id = %s", (ticket.concert_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Geçerli bir konser bulunamadı")
        
        # Bilet ekle
        cursor.execute(
            """
            INSERT INTO tickets (buyer, concert)
            VALUES (%s, %s)
            """,
            (user_id, ticket.concert_id)
        )
        conn.commit()
        return {"message": "Bilet başarıyla alındı"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 