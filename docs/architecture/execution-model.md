# Plan ve çalıştırma modeli

**Durum:** Benimsenmiş tasarım. **Tarih:** 2026-10-27.

İlk uygulama yalnız offline `draft` üretir: sır, araç sürümü, veri/model içeriği veya uzak yetki doğrulanmadığından `prepared`/onay/yürütme durumuna geçmez. Şema/seçim ve digest doğrulaması, aşağıdaki tam execution bağlarının yerine geçmez. [Uygulanan CLI sınırı](../reference/cli-contract.md#uygulanan-alt-küme).

## Planın içerdiği bağlar

Plan; görev türü, veri/model sürümü ve hash'leri, seçilen araç/sürüm, ortam, etkiler, maliyet tahmininin kaynağı/tarihi, parametre eşleme raporu ve deadline politikasını içerir. Kullanılan her hizmet için aşağıdaki bağlar da kanonik temsile ve onay digest'ine dahildir:

| Bağ | Anlam |
|---|---|
| `service_id`, `service_origin`, `api_base_path` | Platform/LLM gibi hizmet kimliği, normalleştirilmiş scheme/host/etkin port ve API kök yolu |
| `account_id`, `project_id` | İşlemin hedeflediği hesap ve gerekiyorsa proje |
| `credential_id`, `credential_revision` | Kullanılan yetkilendirme bilgisinin sır olmayan opak kimliği ve değişimde yenilenen nesli |
| `authorization_scope` | İşlem için doğrulanmış izinler ve kaynak sınırları |

`credential_id` anahtarın kendisi, öneki/soneki veya ham hash'i değildir. Sağlayıcının sır olmayan anahtar kimliği/sürümü kullanılabilir; bunlar yoksa yerel sır yönetimi opak kimlik ve değişim nesli sağlar. Bir env/keychain referansının aynı kalması, değerinin değişmediğine kanıt değildir. Anahtar değişimi saptanamıyor veya gerekli yetki kapsamı doğrulanamıyorsa uzak yürütme için geçerli bağ kurulmuş sayılmaz. Salt yerel görevde kullanılmayan hizmet bağı gerekmez; eksik uzak bağları olan offline plan uzak yürütme onayı sağlamaz.

Plan sır değeri içermez. Bu bağların tamamı dahil kanonik temsilin digest'i ve şema sürümü onayla ilişkilendirilir.

Plan/capability/registry hedef eşlemesinin byte düzeyindeki ayrıntısı [credential binding v1](../reference/credential-binding-v1.md) olarak Accepted ADR-0012 ile benimsenmiştir. Etkin 443 portunun origin metninden çıkarılması ve eski offline Plan'ın değiştirilmeden karşılaştırılması orada tanımlanır; tasarım onayı ürün uygulaması veya kabul kanıtı yerine geçmez.

Araç seçimi ve tüm önemli girdiler plan hazırlığında çözülür. `run` sırasında sürüm/executable, hizmet origin'i/API kökü, hesap/proje, yetki kimliği/nesli/kapsamı veya veri değişmişse eski plan uygulanmaz; yeniden planlama ve etki politikasına göre yeni digest'e bağlı onay gerekir. Aynı profil adı bu kontrolün yerine geçmez. Uzak tahminin geçerlilik sınırı ve bilinmeyen maliyet açık kalır.

```mermaid
stateDiagram-v2
    [*] --> draft
    draft --> prepared: girdiler ve yetenekler doğrulandı
    prepared --> awaiting_approval: etki onayı gerekli
    awaiting_approval --> prepared: planla bağlı onay
    prepared --> submitted: kayıt ve gönderim
    submitted --> running: uzak iş bulundu
    submitted --> unknown: sonuç belirsiz
    submitted --> cancelled: sağlayıcı iptali doğrulandı
    running --> unknown: yetkili durum okunamıyor
    unknown --> running: uzlaştırma
    unknown --> succeeded: sonuç ve teslim doğrulandı
    unknown --> failed: kesin başarısızlık
    unknown --> cancelled: uzlaştırmada iptal doğrulandı
    running --> succeeded: görev ve teslim tamam
    running --> failed: kesin hata
    running --> cancelled: durdurma doğrulandı
    prepared --> cancelled: gönderim öncesi iptal
```

Bu operasyon modeli uzak sağlayıcının ham durumlarını silmez. Execution ve delivery alt durumları ayrı saklanır: örneğin eğitim tamam ama indirme bekliyor olabilir. `succeeded`, görev sözleşmesindeki teslim koşulu da sağlandığında kullanılır.

## Yan etki öncesi sıra

1. Profil, görev, araç, ortam ve planı doğrula; her hizmetin güncel hedef, hesap/proje ve yetki bağını onaylı digest'teki bağla karşılaştır. Kullanılacak sır bu doğrulanmış bağa ait olmalı; denetimden sonra profil/env yeniden çözülerek başka sır veya hedef seçilmez. Bağ değişmiş veya doğrulanamıyorsa yan etkiyi başlatma.
2. Etki/onay politikasını uygula; kullanıcıdan aynı geçerli plan için gereksiz tekrar onayı isteme.
3. Kalıcı operation/attempt ve gerekiyorsa bütçe rezervasyonunu işlemsel kaydet; yazılamıyorsa başlatma.
4. Sahiplik lease'i ve fencing token'ını doğrula; sağlayıcı destekliyorsa kayıtlı idempotency/correlation anahtarını kullan.
5. İsteği veya alt süreci başlat; ham kimliği ve sonucu kaydet.
6. Sonucu ve artefakt teslimini doğrula; rezervasyon/gerçek tüketimi uzlaştır.

Yerel lease veya idempotency kaydı, uzakta tam bir kez çalıştırma garantisi yaratmaz. Sağlayıcı desteği yoksa yanıt kaybı unknown kalır ve başka sahibin aynı işi yeniden göndermesi engellenir. Yakın zamanlı benzer model/veri işi kesin korelasyon kanıtı sayılmaz.

## İptal ve toparlanma

Yerel izlemeyi durdurmak uzak eğitimi durdurmaz. `jobs stop` etkiyi önizler, sağlayıcının durdurma sonucunu bekler veya belirsizliği kaydeder. Kısmi dosya/çıktı kaydı korunur; tamamlanmış gibi adlandırılmaz. Sahiplik devrinde günlük ve plan okunamıyorsa yeni yürütüm başlamaz.

`submitted` veya `unknown` işlem, kayıtlı uzak kimlik/korelasyon üzerinden aynı işin sağlayıcı tarafından iptal edildiği doğrulanırsa `cancelled` olur. İptal isteğinin kabulü, timeout, yerel izleyicinin kapanması veya tek başına işin bulunamaması iptal kanıtı değildir; sonuç belirsizse `unknown` korunur. Ham sağlayıcı durumu ve doğrulama kaynağı işlem kaydına eklenir.

Salt okunur istek, idempotent dosya PUT'u ve kaynak oluşturan POST aynı retry politikasını kullanmaz. Deneme ve toplam deadline, kullanıcı işinin bütün süresini kapsar. [Durum saklama](data-and-state.md), [CLI sonucu](../reference/cli-contract.md).
