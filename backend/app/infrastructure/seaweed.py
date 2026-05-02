import httpx
from app.config import settings


async def assign_volume() -> tuple[str, str]:
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{settings.seaweed_master_url}/dir/assign")
        data = resp.json()
        return data["fid"], f"http://{data['url']}/{data['fid']}"


async def upload_file(file_path: str, content_type: str = "video/mp4") -> str:
    fid, upload_url = await assign_volume()
    async with httpx.AsyncClient() as client:
        with open(file_path, "rb") as f:
            await client.post(upload_url, content=f,
                              headers={"Content-Type": content_type})
    return fid


def get_public_url(fid: str) -> str:
    return f"{settings.seaweed_master_url}/{fid}"
