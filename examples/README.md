# مثال‌ها و دامنهٔ اثباتشان

`hyperframes/index.html` یک نمونهٔ هشت‌ثانیه‌ای تایپوگرافی و نمودار دادهٔ آزمایشی است. `engines/remotion/src/index.jsx` همان اصول را با React و spring/interpolate نشان می‌دهد. این‌ها قالب تولید همهٔ سفارش‌ها یا نمونهٔ کیفیت نهایی خبری نیستند؛ برای ابزار، فونت، حرکت و صدا تست عملی‌اند.

```powershell
node scripts/prepare-examples.mjs
npm run hf -- check .local/examples/hyperframes --json
npm run hf -- preview .local/examples/hyperframes
npm run hf -- render .local/examples/hyperframes --output .local/examples/hyperframes/renders/demo.mp4 --workers 1
node scripts/remotion.mjs studio engines/remotion/src/index.jsx
node scripts/remotion.mjs render engines/remotion/src/index.jsx KalamDemo .local/examples/remotion-demo.mp4
```

کتابخانهٔ `library/index.html` در مرورگر محلی قابل جست‌وجو و فیلتر است. هر کارت می‌گوید چه موتور و تکنیک‌هایی دارد و کد یا رجیستری از کجا باز می‌شود. تکنیک‌های رسانهٔ واقعی به فایل مجاز همان سفارش نیاز دارند؛ از چهرهٔ واقعی یا عکس خصوصی قبلی به‌عنوان نمونهٔ مشترک استفاده نشده است.
