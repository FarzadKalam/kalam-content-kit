"""Inspect supplied font metadata without executing anything in the font archive.
Requires fonttools + brotli in an optional local Python environment.
Extraction is deliberately separate; only a directory of fonts is read here.
"""
import argparse,json,hashlib
from pathlib import Path
from fontTools.ttLib import TTFont
def inspect(p):
    with TTFont(p,lazy=True) as f:
        n=f['name'];c=f.getBestCmap() or {};axes=[]
        if 'fvar' in f:
            axes=[{'tag':a.axisTag,'min':a.minValue,'default':a.defaultValue,'max':a.maxValue} for a in f['fvar'].axes]
        return {'file':str(p),'family':n.getDebugName(16) or n.getDebugName(1),'style':n.getDebugName(17) or n.getDebugName(2),
          'postscriptName':n.getDebugName(6),'weight':f['OS/2'].usWeightClass if 'OS/2' in f else None,
          'axes':axes,'persianLetters':all(v in c for v in [0x067e,0x0686,0x0698,0x06af]),
          'version':n.getDebugName(5),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
def main():
    p=argparse.ArgumentParser();p.add_argument('directory');p.add_argument('--output',required=True);a=p.parse_args()
    result=[]
    for file in sorted(Path(a.directory).rglob('*')):
        if file.suffix.lower() in ['.ttf','.otf','.woff','.woff2']:
            try:result.append(inspect(file))
            except Exception as e:result.append({'file':str(file),'error':type(e).__name__})
    Path(a.output).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'Inspected {len(result)} font files')
if __name__=='__main__':main()
