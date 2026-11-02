# Platform upload tüketici sözleşmesi

**Tarih:** 2026-11-02. **Durum:** ADR-0026 kapsamındaki gerçek adaptör için dar wire sözleşmesi; ürün adaptörü ve canlı upload kabulü henüz tamamlanmadı. [Politika/current/onay](dataset-upload-v2.md) ve [storage portu](dataset-transfer.md#p02-2f-private-storage-port-sözleşmesi) ayrı kanonik kaynaklardır. Bu belge grant, fiyat veya genel provider API garantisi tanımlamaz.

## Kaynak ve güven sınırı

Kayıtlı profil `evren-platform-observed-upload-v2`, policy 2'dir. [Sabit SDK](https://github.com/speker/evren-sdk/blob/f4eaa4a71f324e61058f24fb90c0aec7a58ae24f/evren_sdk/client.py), [kamu istemcisi/guide kaynak kaydı](../research/p02-2-public-source-receipt.json), [beş GET](../research/p02-2-five-get-observations.json) ve [create/detail/my-role araştırması](../research/p02-2-private-create-observations.md) yalnız tüketilen şekil ve rota kanıtıdır. SDK kurulmaz veya kodu kopyalanmaz. İlk yanlış ID-detail GET'in 405 sonucu tarihsel başarısızlık olarak kalır.

Profil `UploadGrant` veya `UploadCostBoundV2` üretemez. Geçerli gözlemde authority `not_exposed`, maliyet null kalır; default `verified_only` bu profille yürütülebilir olmaz. Yalnız açık `explicit_attempt` ve uygun bütçe/onay kuralları ayrı v2 kapısını açabilir. Bilinen HTTP/schema/owner/private uyuşmazlığı hiçbir zaman oracle yokluğuna dönüştürülemez.

## Ortak decode ve yerel alan güvenliği

Kontrol yanıtı en çok 1 MiB, UTF-8 strict JSON; duplicate/nonfinite/BOM/trailing veri ve mevcut depth/node sınırları ret edilir. Bütün ham ağaçtaki string değerler ve yalnız seçilen şeklin tüketilen sabit protokol anahtarları dışında kalan anahtarlar, **seçili credential'ın literal kuralıyla** taranır. Kısa sırda eşitlik, en az 8 UTF-8 byte'ta alt dize eşleşmesi kullanılır; genel sır veya dönüştürülmüş credential tespiti iddia edilmez. Atılan metadata taramayı aşamaz.

Root `success` varsa strict bool=true olmalıdır; 1, false ve string ret edilir. `auth/me` için success=true/data object zorunludur. Diğer object yanıtlarında success varsa data object açılır; success yoksa root doğrudan nesnedir. Liste yanıtı doğrudan array veya success=true/data array olabilir. Metadata public/persistent generic dict'e taşınmaz. Tüketilen alanlar kapalı, strict ve bounded projection'a çevrilir; eksik/yanlış tip kontrol alanı ret edilir.

Her dinamik request segmenti ve body değeri URL/JSON oluşturulmadan önce aynı literal kuralıyla denetlenir; bütün endpoint'e kısa sır eşitliği uygulamak yeterli değildir. Provider username/slug tek ASCII `[A-Za-z0-9_-]` segmentidir (1–128 karakter); slash, percent, dot, query, control ve boş değer ret edilir. Provider UUID canonical herhangi sürümdür; dahili UUIDv4'e çevrilmez. Yerel owner/project/name/license/tag/root alanlarının public özetlere taşınması ayrıca literal denetimden geçer.

## Context, create ve proje bağlantısı

| İşlem | Tüketilen alanlar ve kesin oracle |
|---|---|
| GET auth/me | success=true/data.id canonical UUID. Bildirilen kimliktir; auth veya principal grant değildir |
| GET projects/{project_id} | id, owner_id canonical UUID; org_id zorunlu nullable UUID; visibility strict `private`. ID seçili proje ile eşit; user owner'da owner_id ve me.id seçili owner ile, organization owner'da org_id seçili owner ile eşit olmalıdır. Bu yalnız bildirilen context eşliğidir |
| POST datasets | name/modality/visibility=private/contributions_enabled=false/tags; nonnull license ve organization owner için org_id eklenir. project_id gönderilmez; bağ ayrı etkidir |
| Create yanıtı | id/name/modality/visibility/contributions_enabled/owner_id/org_id tüketilir. id canonical UUID; ad/modality/private/false planla eşit; user owner'da owner_id, organization owner'da org_id beklenen owner ile eşit. org_id eksikliği null sayılmaz. HTTP 2xx veya ID tek başına yeterli değildir |
| POST projects/{project_id}/datasets | Body yalnız dataset_id. Yanıt boş 2xx acknowledgement veya root success=true; dolu logical false/malformed ret edilir. Receipt, ilişkiyi tek başına doğrulanmış saymaz |
| GET projects/{project_id}/datasets | En çok 128 nesnelik liste; her id canonical UUID ve tekil. Exact dataset ID tam bir kez bulunmalıdır; başka ad benzerliği veya ilk kayıt seçilmez. Eksik/tamlığı bilinmeyen liste başarı kanıtı değildir |
| GET datasets | Yalnız kayıtta bilinen exact ID'yi bulmak için page=1..128, page_size=128, scope=owned. Her sayfa en çok 128 kayıt; yinelenen ID, sayfa bütçesi veya kaynak bulunamaması controlled ret/unknown. Ada göre sahiplenme yoktur |
| GET datasets/{owner_username}/{slug} | Rota yalnız exact ID ile bulunan nesnenin güvenli username/slug alanlarından kurulur. Detail ID/name/modality/private/contributions_enabled/owner_id/org_id eşliği zorunludur. `datasets/{id}` detail rotası kullanılmaz |
| GET datasets/{id}/my-role | [V2 my-role şeması](dataset-upload-v2.md#tüketici-profili-http-ve-my-role): strict role/permissions, literal upload etiketi, en çok 30 s current scope. Etiket grant değildir |

Organization context kontrolü kullanıcı üyeliği veya write permission garantisi üretmez. User owner'da org_id nonnull olabilir; kişisel organizasyon ID'si yokmuş gibi varsayılmaz. Create ile sonraki exact-ID detail'deki owner_id/org_id birbirine de eşit olmalıdır. İlk create receipt'inin ID'si hiçbir owned/name aramasıyla değiştirilemez; ID kayıpsa lookup/re-create yapılmaz.

HTTP/schema hata kodları [v2 mandatory-read tablosuna](dataset-upload-v2.md#tüketici-profili-http-ve-my-role) uyar. Create/link etkili istek tek denemedir; her biri önceden kalıcı intent ve tek permit ister. Başarı decode edilemezse yeni istek yapılmaz, mevcut operation ID ile unknown korunur. Salt okuma pagination list tamlığını veya atomik uzak snapshot'ı kanıtlamaz.

## İzleyen dilimler ve kabul

İlk dar kod dilimi yalnız yukarıdaki context/create/link/my-role codec'lerini ve bağımsız negatif fixture'ları sahiplenir. Presign/PUT/confirm, safe object-key ve item pagination ayrıntıları gerçek upload codec'inden **önce** bu referansta kapatılır; bugün bu yollar hazır sayılmaz. Ardından gerçek HTTP bütçe sayacı, ortak koordinatör ve CLI/Python yüzeyi ayrı commit/iki fresh review turuyla uygulanır. Her dilimin tamamlanması a/b/c üst kartlarının bütünleşik/live kabulü yerine geçmez.

Kabul: strict bool/UUID/envelope/eksik-null ayrımı; wrong owner/project/private; exact dataset/detail; kısa/uzun sırın dinamik request alanı veya atılan metadata içinde bulunması; duplicate/nonfinite/UTF-8/byte sınırı; create/link ayrımı ve known-negative hata eşliği. Yalnız fixture yeşili canlı provider desteği sayılmaz. Gerçek producer yeni grant/fiyat kaynağı uyduramaz ve frozen araştırma probe'unu ürün modülü olarak import edemez.
