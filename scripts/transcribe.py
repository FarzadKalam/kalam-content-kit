"""Local-only Persian transcription. User recordings never leave this machine."""
import argparse, json, os, wave
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
os.environ['HF_HOME'] = str(ROOT / '.cache/huggingface')
os.environ['XDG_CACHE_HOME'] = str(ROOT / '.cache')
def main():
    p=argparse.ArgumentParser()
    p.add_argument('wav'); p.add_argument('--output',required=True)
    p.add_argument('--model', default='small')
    args=p.parse_args()
    src=Path(args.wav).resolve(); dest=Path(args.output).resolve()
    if src==dest or dest.exists(): raise ValueError('Output must be a new file, separate from the input.')
    import numpy as np
    from faster_whisper import WhisperModel
    with wave.open(str(src),'rb') as w:
        if (w.getnchannels(),w.getframerate(),w.getsampwidth()) != (1,16000,2):
            raise ValueError('Extract mono 16kHz PCM WAV with: npm run media -- extract input output.wav')
        audio=np.frombuffer(w.readframes(w.getnframes()),dtype=np.int16).astype(np.float32)/32768
    model=WhisperModel(args.model,device='cpu',compute_type='int8',download_root=str(ROOT/'.cache/asr-models'))
    segments,info=model.transcribe(audio,language='fa',word_timestamps=True,vad_filter=True,condition_on_previous_text=False)
    dest.parent.mkdir(parents=True,exist_ok=True)
    result={'engine':'faster-whisper','model':args.model,'language':info.language,'reviewed':False,'segments':[]}
    for s in segments:
        result['segments'].append({'start':s.start,'end':s.end,'text':s.text,'words':[{'word':w.word,'start':w.start,'end':w.end,'probability':w.probability} for w in s.words or []]})
        partial=dest.with_suffix(dest.suffix+'.partial')
        partial.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    dest.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    partial=dest.with_suffix(dest.suffix+'.partial')
    if partial.exists(): partial.unlink()
if __name__=='__main__': main()
