from app.core.config import get_settings
import uvicorn

if __name__ == "__main__":
    s = get_settings()
    uvicorn.run("app.main:app", host=s.HOST, port=s.PORT, reload=(s.ENV == "dev"))