# Voice Manual QA Checklist

## Setup
- Open `http://127.0.0.1:3002/login`.
- Log in as a normal user or admin.
- Confirm backend health at `http://127.0.0.1:8000/health` shows `llm=ollama` and `qdrant=available`.
- Use Chrome or Edge with microphone access available.

## Browser Permission Check
- Click the mic button.
- Allow microphone permission when prompted.
- Expected: the mic state changes to listening/speaking.
- Failure: if permission is denied, the UI should show a microphone error and no request should be sent.

## Push-To-Talk Test
- Toggle voice mode to `Push`.
- Click mic to start recording.
- Say: `hiệu trưởng HUS là ai`.
- Click mic again to stop.
- Expected: transcript appears, answer appears, audio auto-plays, and spoken answer is concise.

## Auto-Stop Test
- Toggle voice mode to `Auto`.
- Click mic once.
- Say: `hiệu trưởng HUS là ai`.
- Stop speaking.
- Expected: recording stops automatically after about 1.2 seconds of silence after speech.

## Silence / Ngập Ngừng Test
- In `Auto` mode, say part of a phrase, pause briefly under 1.2 seconds, then continue.
- Example: `khoa học dữ liệu... học những môn gì`.
- Expected: short hesitation does not stop recording too early.
- No-speech case: stay silent for about 3 seconds.
- Expected: UI says `Mình chưa nghe rõ, bạn thử nói lại nhé.`

## Vietnamese ASR Phrases
- `hiệu trưởng HUS là ai`
- `khoa học dữ liệu học những môn gì`
- `hôm nay tôi cần làm gì`

## Expected Behavior
- Transcript appears as `Đã nghe: ...`.
- Full answer appears in chat.
- Audio answer auto-plays.
- Spoken answer is short and focused.
- Detailed answer and citations remain visible in chat.
- For long RAG answers, speech should say a short summary and indicate details are shown in chat.

## Failure Cases
- Browser blocks autoplay: UI should show a replay/listen prompt; clicking it should play audio.
- Microphone permission denied: UI should show a clear mic error.
- Edge TTS slow: answer text should still appear; audio may arrive later.
- No speech detected: UI should ask the user to try again.
- TTS unavailable: response should degrade to text or fallback audio with metadata showing TTS mode.

## Logs / Metadata To Check
- Admin view: assistant metadata `voice`.
- `metadata.voice_latency_ms`
- `metadata.asr_latency_ms`
- `metadata.assistant_latency_ms`
- `metadata.tts_latency_ms`
- `metadata.audio_duration_sec`
- `metadata.transcript_confidence`
- `metadata.voice_mode`
- `metadata.asr.segments`
- `metadata.tts.mode`
