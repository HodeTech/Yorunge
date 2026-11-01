# Platform probe kaynak arşivi — 2026-11-01

Bu dizin, [davranış receipt’ini](../../p02-platform-reverse-observations.json) üreten yürütücü ve 19 çevrimdışı vakanın **değişmez kaynak snapshot’ıdır**. Sır/hesap verisi içermez. Ürün komutu veya otomatik canlı CI değildir.

| Kaynak | SHA-256 |
|---|---|
| [account_probe.py](account_probe.py) | `a4e91a029e6e280896403fe8e5918b308415a86c02f3258896b4630b5b517a4c` |
| [test_probe.py](test_probe.py) | `ab6e47a303c588931be024093c0adbec314b92aa4ddc648c14f8d0bed7a3ac13` |

account_probe.py hash’i mevcut receipt.probe_sha256 ile birebir aynıdır. Özgün receipt değiştirilmedi. Test hash’i burada arşivlenme anındaki bayt kimliğidir; özgün receipt’te tarihsel test hash’i varmış gibi sunulmaz. Kaynaklar biçim/lint düzeltmesiyle bile yeniden yazılmaz; değişen yöntem yeni dosya/snapshot ve ayrı kayıt gerektirir.

## Ağsız yeniden inceleme

Repo kökünde, mevcut dev ortamıyla:

```sh
.venv/bin/python -m pytest docs/research/probes/platform-20261101/test_probe.py -q
```

19 parametrik vaka yalnız sentetik değerler/geçici dosyalar ve MockTransport kullanır. main() çağıran iki vaka da hazırlık yollarını geçici dizine, API’yi ağ yapmayan test double’ına bağlar; gerçek credentials/scope/state okunmaz. Bu testleri çalıştırmak canlı araştırmayı tekrar çalıştırmaz.

## Canlı tekrar sınırı

account_probe.py dosyasının main() girişini bu arşivden **çalıştırma**. Göreli hazırlık yerleşimi özgün özel yürütme dizinine aittir; bu bir kullanıma hazır kabul aracı değildir. Özgün koşu bir kez 6 GET/6 attempt ile bitti. Yeni bir proje/kapsam ancak ayrı amaç, baştan sayaç/deadline, güvenli yerel hazırlık ve gerçek kullanıcı yetkisiyle incelenir; helper kopyalamak, receipt silmek veya dosya adını değiştirmek eski bütçeyi sıfırlama izni değildir.

Kaynak erişilebilirliği yöntem denetimini sağlar; kaynak/receipt hash’i, dosya mtime’ı ve yerel yeniden test ağ olayına bağımsız attestasyon değildir. [Araştırma kapsamı ve sonuçlar](../../p02-platform-reverse-engineering.md).
