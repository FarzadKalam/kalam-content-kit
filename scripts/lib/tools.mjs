import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);
export function binary(name) {
  if(name==='ffmpeg')return require('ffmpeg-static');
  if(name==='ffprobe')return require('@ffprobe-installer/ffprobe').path;
  throw new Error('Unknown local media tool: '+name);
}
