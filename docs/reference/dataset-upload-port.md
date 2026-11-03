# Upload gerçek HTTP portu

**Tarih:** 2026-11-03. **Durum:** P02-2q.1 immutable arm yerel verified; q.2 gerçek kontrol çağrıları iki fresh turla yerel verified. Ortak resource owner takibi q.2a review aşamasında. PUT/items q.3 ve controller henüz tamamlanmadı. Accepted ADR-0024/0025/0026/0027; [provider codec](platform-upload-consumer.md), [HTTP quota](dataset-upload-http.md), [receipt/current](dataset-upload-v2.md), [güncel input](dataset-upload-preparation.md) temel alınır. Yeni grant/pricing/target/format veya retry politikası yoktur.

## Sahiplik ve hazırlanan çağrı

ObservedUploadPort, current UploadScope/BoundCredential snapshot'ı, exact official Platform HttpCredential, strict saved DatasetUploadPlanV2/Manifest ve aynı UploadBudget/UploadHttpxTransport'a bağlı private adapter'dır. BoundCredential ID/revision/epoch current scope ile, HttpCredential.secret aynı captured SecretValue nesnesiyle eşleşir. Write call'lar current scope=saved plan scope ister. Read-only items güncel scope'u saved exact resource'a scope_target ile bağlar; credential rotation/reset historical plan/baseline'ı yeniden yazmaz ve kaynak dosyayı hash'lemez. Bu port registry/HMAC/store/clock yetki kapısının yerine geçmez; caller controller bu kapıları final repository fazında uygular. Plan scope/target/credential, manifest/reference ve request_limits budget ile eşleşir. Direct provider seçimi presign/network öncesi unsupported_combination kalır. Public caller port, raw client, permit, verified flag veya response enjekte edemez.

Her effect için private PreparedUploadCall, **intent'ten önce** typed scope/parametre/URL/body/descriptor bağını doğrular ve aynı bütçeden request/PUT/response slotunu ayırır. Create/link/presign/confirm HttpRequest yalnız kayıtlı exact method/endpoint/query ve aynı credential'dır; PUT yalnız strict PresignedUpload/FileContext/DescriptorByteSource ve aynı proxy credential'dır. Reservation etki izni değildir. Kaynak descriptor/lazy source konstruktoru dosya okumaz; input'un güncel tam hash/metadata kapısı controller/repository tarafından uygulanır.

Çağrı plan/op/stage/file index ve güvenli semantic request digest'ine bağlanır. Digest aynı approved manifest/plan, accepted dataset ID ve bağımsız yerel file-binding'i kullanır; raw provider key/URL/body hash'i değildir. Mevcut repository semantic request kuralı tek ortak fonksiyona taşınabilir; V1/V2 golden byte'ları değişmez. Execute yalnız repository'nin COMMIT/final gate sonrası tek seferde ürettiği private UploadArm paketini alır: immutable intent snapshot, aynı tek kullanımlık DispatchPermit ve aynı sabit deadline. Ayrı permit/deadline argümanı veya sonradan oluşturulmuş tuple kabul etmez. Generic DispatchPermit PID/one-shot semantiği değişmez; UploadArm sıradan çağıran tarafından kurulamayan private issuance girişi, aynı PID/thread, tek claim ve copy/pickle/repr engeli taşır. Eski private tuple unpack/index erişimi test/geçiş için korunabilir; yeni port bu parçaları ayrı almaz. Bu, bağımsız bir DB attestasyonu değildir: commit kökenini trusted repository issuance sağlar; host içinde keyfi private kod çalıştırmaya karşı sandbox iddiası yoktur. Intent operation/kind/index/digest bağı yanlışsa fiziksel deneme/permit tüketimi başlamaz. PID/thread/owned session ve call tek kullanım sınırı korunur; kopyalama/pickle/çıktı/repr private veri taşımaz.

Yerel hazırlık veya arm reddinde henüz başlamamış reservation açıkça kapatılır; başlamış deneme/byte sayacı geri alınmaz. Call/source/response aynı async task'ta success/error/cancel sonunda kapanır. Cleanup birincil belirsizlik/CancelledError'ı değiştirmez. Kullanılmayan permit veya refund durable intent'i kaldırmaz; controller bir arm/dispatch hatasından sonra workflow'u sürdürmez.

## Kapalı aşama sonuçları

| Aşama | Private request ve geçerli dönüş |
|---|---|
| create | codec create body → tek POST datasets; strict create DTO → CreateReceiptV2 + immutable ProviderDataset. ID/owner/name/modality/private/false/1 MiB raw/literal kuralları korunur |
| project_link | codec link body → tek POST projects/{id}/datasets; strict boş/success ack → accepted StageReceipt v1; membership ayrıca okunur |
| presign | dosya başına codec body → tek POST datasets/{id}/upload/presign; strict private descriptor → accepted StageReceipt v1 içinde yalnız local_binding. Raw key/URL descriptor'da ephemeral kalır |
| PUT | lazy bounded descriptor kaynağıyla tek PUT; StorageResponse ve source EOF exact byte/SHA eşliği + strict 64 KiB ack → accepted StageReceipt v1 sent bytes/hash/local binding |
| confirm | exact descriptor/context body, skip_dedup=true → tek POST confirm; created=1, mevcut accepted confirm sayısı+1 ve duplicate=0 oracle → accepted StageReceipt v1 local binding |

Receipt recorded_at gerçek gözlem anıdır; intent/lease bitmişse geçmişe clamp edilmez. Repository aynı intent/owner/time/credential/plan bağını tekrar kontrol ederek receipt'i kaydeder. Port DB açmaz veya permit üretmez. New create V1 receipt veya raw key receipt'e konmaz.

Bu profilde generic non-2xx/timeout/transport/malformed/partial sonuçtan **kesin rejected receipt üretilmez**; güvenli mevcut hata yükselir. Mevcut StageReceipt.rejected biçimi ve fixture/history korunur; generic status'tan sıfır uzak etki kanıtı türetilmez. Aktif controller kalıcı intent sonrası hata/belirsizliği operation_uncertain/5 + aynı ID ve uygun best-effort marker'a çevirir; retry/new create/URL yenileme/fallback yoktur. Ayrı readonly reconcile source error istisnası v2 referansında kalır.

Bütün N presign descriptor'ı doğrulanıp raw key/exact target bijeksiyonu geçmeden ilk PUT yoktur. PUT en çok iki worker, confirm publication seri ve doğru accepted-count ile olur; bu sıralama controller sorumluluğudur. Port her bağlamı tek başına da kontrol eder; başka dosyanın descriptor'ı veya aynı local binding/client_uid karışımı kabul edilmez. Stage receipt/dataset ID atomikliği repository sorumluluğudur.

## Salt okuma öğe metadata'sı

Known exact dataset için registered GET datasets/{id}/items, limit=128 ve yalnız dönen opaque cursor. Bütün çağrılar aynı read budget/deadline/response guard'a dahildir; sayfa başına ≤128 ve en çok128 sayfa. Bütün projection bounded en fazla manifestin128 öğesi; beklenenN üstü/eksik, değişen total, duplicate item ID/ad/cursor veya yanlış dataset unknown bırakan invalid_response'tur. Next_cursor=null bitişi, total=N ve exact path/size/non-null SHA256 bijeksiyonu zorunlu; ETag hash değildir. Empty/partial veri başarı diye dönmez.

Port item DTO/ordered metadata'yı private döndürür; grant veya TransferVerification proof'unu kendi başına üretmez. Proof controller'ın tam accepted graph, current read policy, immutable create-detail ve membership kanıtından sonra kurulacaktır. Remote byte download/hash doğrulaması yapılmaz; metadata seviyesi ve remote_bytes_verified=false değişmez.

## Kabul ve dilimler

Q.1 UploadArm issuance/claim ve ortak semantic request kuralı; q.2 effect call/quota + create/link/presign/confirm actual TLS ve strict receipt/descriptor; q.3 bounded PUT/source/hash + metadata pagination/reducer. Her dilim commit ve iki fresh review/fix turu. No-permit/wrong-intent/digest/credential/budget/call reuse, başka arm'dan permit parçalama veya büyütülmüş deadline tuple'ı zero wire; gerçek effect fiziksel attempt1 ve read≤2; status/redirect/timeout/body malformed/oversize/compression/raw secret/lost response/cancel/close; local UUID ağda yok, provider key/URL receipt/DB/log/exception/serialization'da yok. Normal/partial/early close pool/FD/quota kapanışı, exact server bytes/hash, descriptor swap ve metadata duplicate/change/null hash sınırları gerçek TLS'te sınanır.

State controller ile bütünleşik replay/kill/marker/public sentinel, API/CLI, native16/256/1024 MiB/kurulum/source CI ve ayrı live kabulü sonraki r/public/c dilimleridir. Bu reference hedefidir; mevcut codec/meter/p yerel verified durumu gerçek port kabulü yerine geçmez.
