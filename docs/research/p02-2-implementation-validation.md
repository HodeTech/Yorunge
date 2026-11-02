# P02-2 uygulama ve kabul kaydı

**Tarih:** 2026-11-02. **Dal:** feat/p02-2-private-upload; development tabanı 50d68b1, P02-1 kapanışı 973cec5. **Durum:** Yerel temel uygulanıyor; remote producer/upload/live kabulü yoktur. ADR-0024/0025 Accepted; [hazırlık ve yetkili beş GET](p02-2-readiness-review.md) ayrı kanıttır. 200 CR geliştirme tavanı fiyat veya write yetkisi değildir.

## Adım 1 — P02-2d yerel plan sözleşmesi

Ayrı strict upload scope/root/manifest referansı/parameters/storage/grant/cost/plan ve approval wire'ı ile private application snapshot factory uygulandı. Literal canonical plan/approval fixture'ları; manifestin canonical encoded byte hash'i ile iç digest ayrımı; sıralı blocker reducer; exact yetki/maliyet scope ve en erken expiry; plan/intent/semantic binding digest'leri ve onay bağları doğrulanır. Prepared snapshot bile executable=false'tur; public caller proof/verified flag almayan kompozisyon henüz ürün CLI'sına bağlanmadı. Fixture grant/cost nesneleri ürün producer'ı değildir.

Mevcut local manifest ve execution/Recipe/jobs wire/digest'leri değiştirilmedi. Yerel tarama veya current authority bu pure factory'den uydurulmaz; factory yalnız trusted composition'ın yakalanmış girdisini seal eder. Kalıcı kayıt/CLI, sonraki P02-2e ve üst a/c kabullerindedir.

İlk uygulama kontrolü: yeni upload sözleşmesi + mevcut manifest ve core boundary kümesinde **420 passed / 2,78 s**; iki yeni kaynak strict mypy ve Ruff format/lint geçti. Son raw byte sınırı/constructed instance negatifleriyle hedefli küme **422 passed / 2,69 s** verdi; tüm src/scripts strict mypy **82 dosyada** geçti. **164 Markdown, 6 skill/27 kart** ve diff denetimleri geçti. Yeni kaynağa ait native referans henüz alınmadı. Adımın iki fresh review turu henüz tamamlanmadı; kart verified değildir.

## Kaynak ve ölçüm sınırı

Hazırlık aşamasındaki 375 arşiv ve üç mevcut v3 referans, o sırada değişmemiş eski runtime kaynağını doğruluyordu. Yeni src/test değişimi sonrası bu referanslar yeni kaynağın kabulü sayılmaz; paket sonunda yeni isimli fresh startup/jobs/dataset ve upload-native ölçümler alınır. Eski başarısız veya başarılı ölçümler ezilmez. Bu adımda tam takım/build/native veya yeni hesap çağrısı yapılmadı; dış create/link/format/storage/price kapıları korunur.
