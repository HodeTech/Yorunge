# P02-2 uygulama öncesi belge, kod ve kaynak incelemesi

**Tarih:** 2026-11-02 Europe/Istanbul. **Dal/taban:** `feat/p02-2-private-upload`, development `50d68b1`; kapanış commit'i `973cec5`. **Durum:** Hazırlık; ADR-0024/0025 Proposed. Ürün kodu/testi, canlı hesap çağrısı veya upload kabulü değildir.

## Yöntem ve mevcut belge incelemesi

AGENTS/ajan çalışma rehberi; implement-task/plan-task/contract-change/review akışı; current/roadmap ve P02 fazı; ürün kapsamı/matris; datasets, mimari ve user journey; güvenlik/UX/test/performans/hata/belgeleme/kanıt/Git standartları; ADR-0011–0018/0020–0023'ün ilgili kararları; credential, capability, execution, operation/state, HTTP/stream, discovery ve manifest referansları karşılaştırıldı. İki bağımsız hazırlık ajanı mevcut state/operation/HTTP kodunu ve kapsam/bağımlılık/otorite belgelerini salt okudu. Önceki araştırma ve kullanıcı kılavuzu bilgisi güncel public web/SDK kaynağıyla yeniden kontrol edildi. Öneriler bunların üzerine yazıldı; gözlem uygulama desteği sayılmadı.

Kamu kaynakları credentialsız HTTPS GET ile alındı; web okuyucusu guide adresini açamadığı için bounded doğrudan HTTPS fallback kullanıldı. Toplam **13 GET / 1.329.541 byte**, redirect yok; her istek 8–10 s faz ve 64 KiB–2 MiB dosya tavanıyla sınırlıydı. İlk sekizli seri 2,393 s içinde bitti; sonraki bağımlı kaynaklar ayrı küçük okumalardır, tüm araştırmanın tek 30 s atomik koşu olduğu iddia edilmez. JavaScript çalıştırılmadı, SDK kurulmadı/import edilmedi. Anahtar/config/özel hesap kullanılmadı; **0 hesap isteği, 0 etkili istek**. HTML/bundle/SDK kaynak gövdeleri repoya kopyalanmadı. Tam URL/byte/SHA [kaynak receipt'indedir](p02-2-public-source-receipt.json); hash kaynak kimliğidir, imza veya API garantisi değildir.

## Doğrulanmış hazırlık boşlukları ve aksiyonlar

| Bulgu | Mevcut kanıt | Hazırlık aksiyonu |
|---|---|---|
| Çok aşamalı etki mevcut tek start'a sığmaz | `application/operations.py` tek start; `operation_repository.py` kalıcı latch sonrası yeni attempt'i reddeder; read portu yalnız observe | ADR-0024: ayrı transfer plan/operation ailesi, workflow + aşama intent/receipt, replay yasağı ve aynı-ID read recovery önerildi |
| Manifest/execution limitleri farklı | Manifest 4.096 dosya/8 MiB; execution 128 input/64 KiB ve yalnız manifest dosyasının hash bağı | Eski wire korunur; ayrı immutable manifest bağlı transfer, tam içerik kontrolü ve açık ilk 128 upload dosya sınırı önerildi |
| Discovery yazma otoritesi değildir | Platform modeli validation=unverified, authentication=unknown, authorization_scope=null | API-key create/link ve exact dataset upload/read yetkisi için ayrı current producer kapısı; fake prepared yok |
| Create ve proje ilişkisi ayrı | Dataset create body'de org_id seçeneği var, project_id yok; project hook ayrı link POST'u gösteriyor | Create→project_link açık aşama/yan etki olarak plana ve ADR'ye eklendi; ilişkisiz başarı yok |
| Signed/proxy hedefler aynı değildir | Service HttpRequest göreli endpoint/bytes≤1 MiB; frontend direct URL'de credentialsız XHR, proxy'de bağlı client kullanıyor | ADR-0025: explicit target sınıfları, önceden allowlist, exact wire URL, auth/cookie/log/expiry ve bounded stream |
| 30 s generic execution lease/bütçesi transfer bütçesi değildir | Operation port deadline'ı lease/total'dan 5 s düşüyor | Yeni transfer için ayrı 900 s plan/onay/toplam, 150 s lease ve 120 s PUT; mevcut execution 30/300 s kuralları değişmiyor |
| Kesinti güvenliği sonraki epike bırakılamaz | P02 fazı P02-2c'yi first-upload read reconciliation sahibi yapıyor | P02-2c show/reconcile ve her aşamada kill/kayıp cevap; P02-3a yalnız etkili güvenli resume |

Bunlar P02-1 veya P01'e ait doğrulanmış ürün kusurları değildir; yeni tüketicinin önkoşullarıdır. Mevcut accepted kararları bu hazırlıkta geriye dönük değiştirilmedi. Eski P02-0 araştırmasındaki upload bilgileri tarihli kaynaktır; bugünkü API davranışı diye kullanılamaz.

## Güncel public kaynakların söylediği ve söylemediği

| Kaynak | Bu turda tüketilen bilgi | Açık sınır |
|---|---|---|
| [Guide](https://evren.ssyz.org.tr/guide), [içerik asset'i](https://evren.ssyz.org.tr/assets/UserGuidePage-DTl0xmcl.js) | X-API-Key, presign→PUT→confirm ve item cursor; UI 500 MB/dosya anlatımı | Normatif auth/replay/fiyat/expiry ve raw strict şema değildir; direct MinIO anlatımı ve proxy örneği ayrı |
| [Dataset API](https://evren.ssyz.org.tr/assets/datasetApi-CA1WYT2w.js) | Create POST; detail owner/org/private alanları; item id/dataset_id/original_filename/file_size_bytes/nullable sha256_hash; items/next_cursor/total | Owner/auth/snapshot ve hash semantiği istemci şemasıyla kanıtlanmaz; `project_id` create alanı görülmedi |
| [Create UI](https://evren.ssyz.org.tr/assets/DatasetListPage-0ZBmWGZj.js) | name/modality/description/visibility/contributions_enabled/license/tags ve seçili org_id | Kişisel owner ve org_id'nin API key ile uygulanma koşulu belirsiz; org yokluğundan yanlış hesap varsayılmaz |
| [Project hook](https://evren.ssyz.org.tr/assets/useProject-C5SXBHgI.js) | `GET projects/{id}/datasets`, `POST projects/{id}/datasets` body dataset_id; ayrı DELETE yolu var | Link auth/idempotency/response şeması canlı doğrulanmadı; DELETE bu pakette kullanılmaz |
| [Role hook](https://evren.ssyz.org.tr/assets/useDatasetRole-BLM7Tb7t.js) | `GET datasets/{id}/my-role`, role/permissions ve upload/edit/read dışı UI yetki isimleri | UI kontrolü backend auth/key-scoping garantisi değildir. Read izin adı bu hook'ta açık değil; uydurulmaz |
| [Upload UI](https://evren.ssyz.org.tr/assets/DatasetDetailPage-BPeje7FE.js) | presign files'ta client_uid; direct_upload_url / upload_url ayrımı; content_type; confirm skip_dedup ve created/actual_count/batch_duplicates; UI retry yapıyor | Retry kopyalanmaz. Direct host/path/expiry/header ve same-hash ad cardinality garantisi yok; frontend fallback matching oracle alınmaz |
| [Sabit SDK client](https://github.com/speker/evren-sdk/blob/f4eaa4a71f324e61058f24fb90c0aec7a58ae24f/evren_sdk/client.py) ve [güncel metadata](https://pypi.org/pypi/evren-sdk/json) | Latest 0.11.0; bütün image bytes'ı okuyan presign/PUT/confirm; credentialed client ve duplicates shortcut | Yörünge için uygun stream/target/receipt/replay adaptörü değildir; import veya kod kopyalama yok |

Kaynak güncelliği araştırma gününe aittir; asset URL'si kalıcı API değildir. Provider'ın bilinmeyen alanları, başarı envelope'u, create response ID/owner/private ilişkisi, link sonucu, upload batch/ad cardinality, current grant ve fiyat için kapalı oracle üretilemedi. Bunlar [başlangıç kapılarıdır](../roadmap/p02-2-delivery-plan.md#başlangıç-kapıları); tahminle doldurulmaz.

## Kullanıcıya sunulan kararlar ve gereken dış bilgi

1. [ADR-0024](../decisions/0024-durable-dataset-transfers.md): Eski execution/Recipe/jobs biçimlerini koruyan ayrı transfer ailesi; görünür create+project link; kalıcı aşama intent'leri, aynı-ID read-only restart; ilk upload ve state/süre kotaları.
2. [ADR-0025](../decisions/0025-isolated-storage-streaming.md): Ayrı auth/target politikasıyla API proxy ve önceden allowlist'e alınmış direct storage, bounded descriptor streaming; signed URL kalıcı/çıktı verisi olmaz.
3. Canlı hazırlık için scoped salt okuma endpoint listesi ve yetkisi; sonraki canlı yazmada exact owner/proje/format/storage hedefi, ücret kaynağı ve azami CR. Önceki discovery anahtar/proje hazırlığı write/cost onayı değildir. Kullanıcıdan key değeri veya ham hesap JSON'u istenmez.

Yeni ADR onayı olmadan bağımlı ürün kodu yoktur. Onay, açık provider sözleşmesi veya fiyatı kendiliğinden doğrulamaz. Onay sonrası local domain/state/TLS fixture adımları bağımsız ilerleyebilir; remote adapter/live kapıları ayrıca kapatılır. Kullanıcının kapsamı, bu kapıları aşmak için sessizce read-only veya ilişkisiz create'a daraltılmaz.

## Review ve doğrulama kaydı

İlk preflight: iki bağımsız salt okunur agent (state/HTTP/code ve scope/docs/authority) ile ana kaynak incelemesi tamamlandı. Bununla yeni yazılmış ADR/metinlerin iki fresh review turu tamamlanmış sayılmaz. Doküman/rehber kontrolleri ve fresh tur sonuçları çalıştırıldıktan sonra aşağıda gerçek sonuçlarıyla kaydedilecektir. Ürün test/build/native ölçüm ve hesap API çağrısı bu hazırlıkta çalıştırılmadı.


### Fresh belge review R1

İlk hazırlık commit'i **2655c2b**, iki yeni reviewer ile state/authority (GPT-6 Astra, high) ve transport/evidence (GPT-6.1 Sol, high) eksenlerinde incelendi. State kolunun iki P2 bulgusu current metin/kodla doğrulandı: ilk prepare/approve için döngüsel approval/owner koşulu; total deadline için eksik 5 s sonuç payı. İkisi aşamaya özgü kapılar ve ortak total/lease/authority/URL formülüyle düzeltildi. Taşıma kolu yeni doğrulanmış bulgu bildirmedi. Ana inceleme ayrıca iki worker'dan birinin hatasında yeni intent/confirm'in durmasını, in-flight diğer etkinin geri alınmış sayılmamasını açıklaştırdı. R1 ürün testi veya gerçek hesap kabulü değildir; ikinci fresh tur düzeltme commit'inden sonra yapılacaktır.
