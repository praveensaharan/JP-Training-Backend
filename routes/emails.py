# routes/emails.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from db import get_connection
import psycopg2
from email_utils import send_email

router = APIRouter()

class EmailCreate(BaseModel):
    email: EmailStr


def insert_email(email: str):
    conn = get_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Failed to connect to the database")

    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO emails (email) VALUES (%s) RETURNING id, email, created_at",
                (email,)
            )
            new_email = cursor.fetchone()
            conn.commit()
            return new_email

    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        raise HTTPException(status_code=400, detail="Email already exists")

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to insert email: {e}")

    finally:
        conn.close()



def get_all_emails():
    conn = get_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Failed to connect to the database")

    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, email, created_at FROM emails ORDER BY created_at DESC")
            emails = cursor.fetchall()
        return emails

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch emails: {e}")

    finally:
        conn.close()


