Import yt_dlp


def download_video(url, output_dir="downloads"):
    ydl_opts = {
        "format": "bestvideo+bestaudio/best",
        "merge_output_format": "mp4",
        "outtmpl": f"{output_dir}/%(title)s.%(ext)s",
        "quality": "highest",
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        print(f"Downloaded: {info['title']}")
        print(f"Saved to: {output_dir}/")


if __name__ == "__main__":
    url = input("Enter the YouTube video URL: ").strip()
    if not url:
        print("No URL provided.")
    else:
        download_video(url)
