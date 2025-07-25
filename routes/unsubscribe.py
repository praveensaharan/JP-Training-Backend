# routes/unsubscribe.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from db import get_connection


router = APIRouter()

class SubscribeRequest(BaseModel):
    email: EmailStr

@router.post("/unsubscribe")
def unsubscribe(req: SubscribeRequest):
    conn = get_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Failed to connect to the database")

    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM emails WHERE email = %s RETURNING id", (req.email,))
            result = cursor.fetchone()
            conn.commit()

        if not result:
            raise HTTPException(status_code=404, detail="Email not found")

        return {"message": "Unsubscribed successfully!"}

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to unsubscribe email: {e}")

    finally:
        conn.close()
