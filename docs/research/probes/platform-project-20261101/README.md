# Seçili proje için ayrı salt okuma kabulü

**Durum:** Kullanıcının hazırladığı boş/private proje için kabul yürütücüsü; ürün backend/CLI seçeneği değildir. Bu kaynak mevcut Accepted discovery yolunu sınar; ADR-0022’yi onaylanmış veya P02-0’ı tamamlanmış saymaz.

[project_probe.py](project_probe.py), önceki [değişmez sayaç/transport/maskeleme kaynağının](../platform-20261101/README.md) doğrulanan **aynı baytlarını** pyc/modül önbelleği kullanmadan derler. Önceki receipt.probe_sha256 ile eşlik kontrol edilir. Kaynak değişikliği kontrollü ret olur; bu hash imza veya server attestasyonu değildir. Özgün önceki kaynak ve receipt değiştirilmez.

## Kapsam

- Kullanıcının verdiği project ID yalnız Git dışındaki `.local/p02-pilot/project-acceptance-input-20261101.json` dosyasından, owner/0600/no-follow kontrolüyle okunur. Özel parent 0700’dür. ID kod/rapor/argv içine gömülmez.
- Mevcut gerçek `api.discover_context` yolu açık project override ile bir kez çalışır: me/orgs/projects/detail için **4 pozitif GET**. Proje seçimi/config dosyası yazılmaz. Yerel mevcut registry/clock capture/final gate aynı kalır.
- Yalnız yeni sınanan detail için ayrıca **1 missing-key GET** yapılır. Önceki üç auth kontrolü tekrarlanmaz. Bu gözlem key değeri veya permission doğrulaması değildir.
- Tek yeni koşu tavanı **5 logical GET / 5 wire attempt / 4 MiB tüketilen raw-body / 30 s cooperative deadline**; retry 0. Önceki 6 GET koşusuna ekleme veya onun tavanının/deadline’ının sıfırlanması değildir. İki ayrı koşu toplanıp tek 8-GET pilotu içinde gösterilemez.
- Pinned HTTP/1.1 read boyutu 64 KiB ön rezervi ve 1 s kapanış rezervi önceki kaynakta korunur. Son session cleanup dönüşünde de toplam deadline tekrar denetlenir; geç dönüş kabul sayılmaz. Limitte daha erken kontrollü durulabilir; fiziksel blok I/O’su için kesin duvar saati garantisi yoktur.
- Project list nonempty, kullanıcı ID’sinin listede bulunması ve detail ID eşliği gerçek DTO üzerinden bool olarak doğrulanır. 404/boş liste/ID farkı/reflected seçili literal, kabul başarısı değildir. Auth unknown/identity unverified/authority null/consistency not_guaranteed ayrıca denetlenir.
- Receipt yalnız schema/type/count/status/bool ve yöntem kaynak hash’i taşır. Raw değer/gerçek ID/key/PII ve header değeri yayımlanmaz. Yeni kaynak/key, upload/model/terms/ödeme/DELETE çağrısı yoktur.

## Ağsız kontrol

Repo kökünde:

```sh
.venv/bin/python -m pytest docs/research/probes/platform-project-20261101/test_project_probe.py -q
```

10 vaka yalnız sentetik input, geçici SQLite/özel dosyalar ve MockTransport kullanır; gerçek hesap dosyası/ağ kullanılmaz. İlk fixture denemesinde buffered httpx.Response raw stream gibi hazırlanmıştı; StreamConsumed ile başarısız oldu. Test fixture’ı gerçek stream ByteStream kullanacak şekilde düzeltildi; bunun için ürün davranışı gevşetilmedi.

## Yetkili canlı giriş

Kaynak ve ön kontroller gözden geçirilmeden çalıştırılmaz. Repo kökü, doğru yerel ürün origin’i ve açık `--execute` gerekir:

```sh
.venv/bin/python docs/research/probes/platform-project-20261101/project_probe.py --execute
```

Bu komut gerçek GET ve yerel registry gözlemi yapar. Çıktı `.local/p02-pilot/platform-selected-project-20261101.json` olarak bir defa rezerve edilir; var olan receipt üzerine yeni koşu başlatılmaz. Başarısız/yarım kayıt silinmez. Kullanıcının proje URL’sini vermesi bu dar salt okuma kabulünün girdisidir; ADR-0022 onayı, key yaratma veya uzak resource mutasyonu değildir.
