// Local-only GFM preview using an already installed marked module; no project dependency.
import fs from 'node:fs';
import path from 'node:path';
import http from 'node:http';
import { createRequire } from 'node:module';
const [rootArg, markedPath] = process.argv.slice(2);
const root = path.resolve(rootArg);
const { marked } = createRequire(import.meta.url)(markedPath);
const text = fs.readFileSync(path.join(root, 'README.md'), 'utf8');
const html = marked.parse(text).replace(/<h([1-6])>(.*?)<\/h\1>/g, (_, level, title) => {
  const slug = title.replace(/<[^>]+>/g,'').toLowerCase().replace(/[^\p{L}\p{M}\p{N}\s_-]/gu,'').replace(/\s/g,'-');
  return `<h${level} id="${slug}">${title}</h${level}>`;
});
const page = `<!doctype html><html lang="th"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>ตัวอย่าง README — ยังไม่เผยแพร่</title><style>
body{margin:0;background:#f4f7f5;color:#18372d;font:16px/1.8 Tahoma,sans-serif}main{max-width:1000px;margin:auto;padding:32px;background:white}img{max-width:100%;height:auto}h1,h2,h3{line-height:1.5}h2{border-bottom:1px solid #d2ded7;padding-bottom:12px;margin-top:44px}a{color:#176751}table{border-collapse:collapse;display:block;overflow:auto}td,th{padding:10px 14px;border:1px solid #d2ded7}pre{overflow:auto;padding:20px;background:#f0f5f2;border-radius:8px}code{font-family:Consolas,monospace}blockquote{border-left:4px solid #226c53;padding-left:20px;margin-left:0}.notice{padding:14px;background:#fff3ce}
</style><main><p class="notice">ตัวอย่าง GFM ในเครื่อง ไม่ใช่หน้า GitHub ที่เผยแพร่แล้ว; Mermaid แสดงเป็น code block ใน preview นี้</p>${html}</main></html>`;
http.createServer((req,res)=>{
  if(req.url === '/' || req.url === '/README.html'){res.setHeader('Content-Type','text/html; charset=utf-8');res.end(page);return;}
  const relative = decodeURIComponent(req.url.split('?')[0]).replace(/^\//,'');
  const target = path.resolve(root,relative);
  if(!target.startsWith(root+path.sep) || !/\.(svg|png|ttf)$/.test(target) || !fs.existsSync(target)){res.writeHead(404);res.end();return;}
  res.setHeader('Content-Type',target.endsWith('.svg')?'image/svg+xml':target.endsWith('.png')?'image/png':'font/ttf');fs.createReadStream(target).pipe(res);
}).listen(8002,'127.0.0.1',()=>console.log('README preview: http://127.0.0.1:8002/README.html'));
