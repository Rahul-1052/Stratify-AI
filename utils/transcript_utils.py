import re
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable,
    RequestBlocked,
    IpBlocked,
)


def clean_transcript(text: str, max_chars: int = 6000) -> str:
    if not text:
        return ""

    text = re.sub(r"\[(.*?)\]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_chars]


def fetch_transcript(video_id: str) -> dict:
    try:
        ytt_api = YouTubeTranscriptApi()
        transcript_list = ytt_api.list(video_id)

        # 1. Manual English
        try:
            transcript = transcript_list.find_manually_created_transcript(["en", "en-US", "en-GB"])
            data = transcript.fetch()
            text = " ".join(chunk.text for chunk in data).strip()
            return {
                "ok": True,
                "text": text,
                "language": transcript.language_code,
                "source": "manual",
                "error": None
            }
        except Exception:
            pass

        # 2. Generated English
        try:
            transcript = transcript_list.find_generated_transcript(["en", "en-US", "en-GB"])
            data = transcript.fetch()
            text = " ".join(chunk.text for chunk in data).strip()
            return {
                "ok": True,
                "text": text,
                "language": transcript.language_code,
                "source": "generated",
                "error": None
            }
        except Exception:
            pass

        # 3. Any translatable transcript -> English
        for transcript in transcript_list:
            try:
                if transcript.is_translatable:
                    translated = transcript.translate("en")
                    data = translated.fetch()
                    text = " ".join(chunk.text for chunk in data).strip()
                    return {
                        "ok": True,
                        "text": text,
                        "language": translated.language_code,
                        "source": "translated",
                        "error": None
                    }
            except Exception:
                continue

        return {
            "ok": False,
            "text": None,
            "language": None,
            "source": None,
            "error": "No usable transcript found."
        }

    except TranscriptsDisabled:
        return {
            "ok": False,
            "text": None,
            "language": None,
            "source": None,
            "error": "Transcripts are disabled for this video."
        }
    except NoTranscriptFound:
        return {
            "ok": False,
            "text": None,
            "language": None,
            "source": None,
            "error": "No transcript found."
        }
    except VideoUnavailable:
        return {
            "ok": False,
            "text": None,
            "language": None,
            "source": None,
            "error": "Video unavailable."
        }
    except (RequestBlocked, IpBlocked):
        return {
            "ok": False,
            "text": None,
            "language": None,
            "source": None,
            "error": "Transcript request blocked by YouTube/network."
        }
    except Exception as e:
        return {
            "ok": False,
            "text": None,
            "language": None,
            "source": None,
            "error": f"Transcript fetch failed: {str(e)}"
        }