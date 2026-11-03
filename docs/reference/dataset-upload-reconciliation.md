# Upload salt okuma uzlaştırması

**Tarih:** 2026-11-03. **Durum:** P02-2s.1 local/current/mandatory probe iki fresh kod turu/fix teyidiyle yerel kapandı. S.2 read lease/items/proof ve gerçek TLS/process-kill regresyonları iki fresh kod turuyla kapandı; P02-2s çalışma dalında yerel verified. [V2 read/terminal/proof matrisi](dataset-upload-v2.md#read-terminal-ve-başarı-grafiği), [ADR-0027](../decisions/0027-durable-created-dataset-context.md) baseline/history ve [original workflow](dataset-upload-workflow.md) kanoniktir. Bu belge yeni auth/fiyat/receipt/success veya retry hakkı tanımlamaz.

## Yerel preflight ve öncelik

Sync/ID/state-dir/flag türü denetlenir; open_existing_store ile exact operation+plan+manifest+receipt grafiği yalnız DB’den okunur. Root veya manifest dosyası açılmaz, config/env henüz çözülmez. Yerel anlam sırası:

| Durum | Loader/network/ownership öncesi sonuç |
|---|---|
| Terminal succeeded/failed/cancelled | operation_conflict/2; geçmiş değişmez |
| V2 historical accepted-create v1 baseline | ADR-0027 require_created_baseline owner/CAS tablosu: operation_uncertain/5, koşullu local marker, sıfır HTTP/yeni lease |
| Unlatched veya dataset ID’si olmayan kayıtta etkin lease | Mevcut cleanup/takeover kapısı operation_conflict/2; yeni hak yok |
| Expired unlatched admission | Mevcut execution izni üretmeyen cleanup → cancelled; yerel sonuç, HTTP yok |
| Latched ama dataset ID yok, lease expired | Mevcut expired cleanup ile unknown; operation_uncertain/5 + aynı ID, HTTP/yeni lease yok |
| Diğer etkin lease; güvenli takeover mümkün değil | operation_conflict/2; lease alınmaz |
| V1 veya v2 verified_only + explicit read flag | invalid_request/2; default grant kapısı bypass olmaz |
| Bu observed producer ile v1/verified_only, flag false | Gerçek current read grant üretilemediği için upload_plan_not_valid/2; private repository’nin gerçek grant’lı tarihsel read davranışı değişmez |
| V2 explicit + flag false, bu producer’da grant oracle’ı yok | approval_required/4; ownership mutation/network yok |
| V2 explicit + flag true ama accepted stage/receipt grafiği eksik | Mevcut expired cleanup ile unknown; operation_uncertain/5, HTTP/yeni read lease yok. Metadata receipt tamamlamaz |
| Tam V2 explicit graph + flag true | Deferred current context/credential ve gerçek bounded read yoluna geçilir |

Etkin lease’in varlığı insan seçimiyle aşılamaz. Terminal ve legacy baseline önceliği kendi kabul edilmiş kapısındadır. Unlatched/missing-ID ve ADR-0027 legacy cleanup kendi kabul edilmiş flag-bağımsız yerel istisnasıdır. Tam ID/baseline kaydında flag false kapısından önce ek cleanup/ownership mutation yapılmaz. Local cleanup ayrı execution izni üretmeyen mevcut CAS/fence yoludur; original access/attempt/permit üretmez. Kimliği bilinmeyen create, local operation ile incelenir; ikinci create veya kalıcı namespace’i aşan yeni plan önerilmez. Eksik receipt’i yalnız metadata eşliği geri getirmez; bu çağrı etkili resume değildir.

## Güncel bağ, kaynaklar ve bütçe

Loader yalnız yerel kapılar geçince saved plan’la çağrılır. Store ID, target/API kökü, hizmet, owner kind/ID ve project niyeti korunur. Saved profile varsayılan credential seçimidir; açık current profile seçimi ancak aynı stable scope_target eşliğinde farklı olabilir, otomatik profil fallback’i yoktur. Current env secret bir kez çözülür; gerçek registry gözlemi kısa store fazında yapılır ve yerel yazı olabilir. Yeni current scope aynı historical resource target’ına bağlanır; credential ID/revision veya store identity epoch/clock generation değişebilir. Historical plan/approval/create receipt mutate edilmez. Farklı store/target/owner/project state_changed/2 ve sıfır remote read’dir. Proof scope current profile/credential/epoch/generation’ı taşır; profile, mevcut scope_target helper’ının stable resource alanlarından biri değildir.

Stored manifest DB’den metadata eşliği için alınır; root/stat/hash veya normal source dosyası gerektirmez. Port/current reader aynı captured secret/bound scope/readonly UploadBudget ve owned session/loop/pool kullanır. Yeni readonly invocation toplam **30 s**’dir; original start’ın 900 s hakkı veya cost bound’u uzatılmaz. Mevcut max logical/physical read ve byte tavanları daraltılmadan uygulanır; read retry ortak ADR-0017 sahibindedir. Hiçbir effect quota/permit üretilmez. Bu ayrı okumanın maliyetinin eski original-start bound’una dahil olduğu iddia edilmez.

## Gerçek read ve kalıcı proof

Immutable accepted CreateReceiptV2 baseline expected alınır. Current producer exact context, owned→detail full baseline (iki owner alanı dahil), membership gözlemlerini tamamlar; upload my-role gerekmez. Kaynak negatifini not_exposed’a çevirmez. Pozitif gözlem final local inspection sonrası toplam budget ve authorization freshness’ini tekrar geçer; expired snapshot dönmez ve checked_at ileri taşınmaz. Current AuthorizationCheck ardından kısa repository acquire_read transaction’ı aynı local koşulları ve current scope/insan seçimi/freshness’i tekrarlar; yalnız read-mode lease/fence verir, write owner/nonce değişmez. Ağdan dönene kadar transaction açık tutulmaz.

Items, aynı credential/session/budget ile tam ordered manifest ad/size/SHA/tekil ID eşliğine indirgenir. observed_at read lease/recovery marker sonrası, ilk items GET öncesidir; authorization ve proof freshness ileri kaydırılmaz. Items deadline yeni readonly toplam−5 s, mevcut read lease/grant expiry−5 s, authorization checked_at+30 s ve en çok 30 s request süresiyle sınırlıdır. Final repository.verified girişte, transaction COMMIT öncesinde ve son yerel fazdan sonra aynı invocation deadline’ını kontrol eder. Deadline COMMIT öncesinde dolarsa proof/control rollback olur; COMMIT sonrasında dolarsa güvenli execution_timeout/2 + aynı ID döner, kalıcı terminal korunur. Bu kontrol noktaları fiziksel duvar saati garantisi değildir. Final repository.verified tam accepted graph, CreateReceiptV2, current scope/epoch/generation/recovery floor/owner/CAS ve metadata’yı tekrar doğrular. Succeeded/metadata_verified yalnız durable transaction sonucu olabilir; authority/remote_bytes doğrulanmış sayılmaz. Restart read için eski write approval’ının etkin olması gerekmez; v2 explicit flag ve gerçek current read kapısı gerekir. Eski onayın expiry/revoke’u geçmiş write’ı geri almaz veya yeni write açmaz.

## Hata, iptal ve yarış

Mandatory read veya items 401/403/429/5xx/transport/schema negatifinin güvenli kaynak kodu ve operation ID korunur. Current negatif check veya aynı current scope’ta gerçekten gözlenmiş items negatifinden üretilen failure check, mevcut read_failed kapısına gider: mümkünse unknown/read_unavailable, hiçbir execution-failed veya yeni grant yoktur. Önceden aynı read_unavailable marker’ı olsa da source negative güncel credential/scope/freshness/takeover gate’lerini atlayamaz; adapter marker kısa yolu yetki denetiminin yerine geçmez. Source hatası bilinen read ret’iyken fallback/yeniden write yoktur. Scope/clock/lease/store/kapasite gibi yerel retler read grant yokluğu diye yutulmaz; kendi güvenli hata kodu korunur. Marker owner/CAS/store reddi eski business state’i bırakabilir; marker yazıldı iddiası yoktur, mevcut repository hata önceliği geçerlidir.

Gerçek Task.cancel response/session cleanup ve sahip olunan read lease için mümkün olan local bırakma denemesinden sonra yeniden yayılır. SIGINT request_cancelled/6 + bilinen ID’dir; uzak iptal değildir. Read-only çağrı write-start belirsizliği gibi yeni etki üretmediğinden kaynak hatalarını genel operation_uncertain/5’e dönüştürmez; eksik baseline/graph/ID yerel 5 kapıları yukarıdadır. Yarışta terminal olmuş kayıt düşürülmez. Proof COMMIT sonrası cevap kaybı aynı terminal kayıtla local bulunur; sonraki reconcile terminal kapısında durur. Public projeksiyon ayrı summary’dir; full view/receipt/baseline/error body/raw key/URL dışarı çıkmaz.

## Kabul sınırı

Local retlerde dependency trap ve sıfır HTTP; tam unknown→gerçek current read→aynı-ID durable metadata success; credential rotation/reset/clock/scope/active owner; mandatory/items kaynak hata ve marker yarışı; gerçek Task.cancel/kill/receipt/proof commit kaybı; no source/no effect meter ve terminal history. Her cohesive kod dilimi commit ve iki fresh turla kapanır. Public summary/API/CLI/sentinel, native/kurulum/source CI/kanıt/ayrı live üst c tesliminde açık kalır.

Kod sırası: s.1 local preflight/current binding/gerçek mandatory read gözlemini private olarak bağlar; s.2 aynı açık invocation’daki gözlemi read lease/items/proof ve tam hata/kesinti yoluna bağlar. S.1 ayrı public komut veya metadata success değildir. Her dilim kendi commit/iki fresh turuyla kapanır.
