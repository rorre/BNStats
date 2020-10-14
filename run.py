from bnstats.app import create_app
import uvicorn
import os

os.chdir("bnstats")
if __name__ == "__main__":
    uvicorn.run(create_app(), host="0.0.0.0", port=8000)
