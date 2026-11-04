# Private dataset aktarımı

**Tarih:** 2026-11-03. **Durum:** P02-2t ortak CLI/Python akışı ve iki fresh review turu çalışma dalında yerel tamamlandı. R5 canlı metadata ve 06 güncel kaynak native kabulü geçti; üst c son üç ortam CI/altı kurulum ve kalıcı saklamayı bekler. [Kesin public sözleşme](dataset-upload-public.md), [güncel durum](../roadmap/current.md).

Önce yerel dosyaları inceleyin, seçtiğiniz owner/projeyi kontrol edin ve planın tam digest’ini onaylayın. Aktarım bir kez gönderilir. Uzak metadata eşliği, dosyaların uzaktan indirilip hash’lendiği veya yetkinizin doğrulandığı anlamına gelmez.

## Hazırlık

[Kaynak kurulumunu](../../README.md#çalışan-başlangıç) tamamlayın. Kendi config/state’iniz varsa onları kullanın; yeni bir çalışma için:

```sh
.venv/bin/yorunge init --config .local/upload/config.toml
.venv/bin/yorunge state init --state-dir .local/upload/state
```

Config init mevcut dosyayı ezmez. Varsayılan profil `EVREN_PLATFORM_API_KEY` env referansını kullanır. Anahtar hazır değilse **Bash terminalinde**, aşağıdaki komutu tek başına çalıştırıp gizli girişe anahtarı yazın:

```bash
read -r -s -p 'Platform API anahtarı: ' EVREN_PLATFORM_API_KEY
```

Giriş tamamlanınca değişkeni aynı terminaldeki komutlara aktarın; bu komut değeri yazdırmaz:

```bash
export EVREN_PLATFORM_API_KEY
```

Mevcut [P02 özel credential dosyası](../p02-account-setup.md#hazırlıktan-normal-discoveryye) ürün tarafından doğrudan okunmaz; o rehberdeki çocuk-süreç env aktarımı da kullanılabilir. Anahtar CLI argümanı değildir. Farklı terminaldeki env seçiminiz bu terminale taşınmaz.

## Planı inceleyip açıkça onaylayın

Küçük, ayrı bir dosya klasörü seçin. Gizli dosyalar dahil bütün alt dosyalar envantere girer; manifest kökün dışında olmalıdır. OWNER_ID ve PROJECT_ID yerine kendi seçiminizi yazın; bir ID’yi görmek yetki kanıtı değildir.

```bash
ROOT='./data'
MANIFEST='.local/upload/manifest.json'
CFG='.local/upload/config.toml'
STATE='.local/upload/state'
OWNER_ID='YOUR_USER_UUID'
PROJECT_ID='YOUR_PROJECT_UUID'

.venv/bin/yorunge datasets inspect "$ROOT" --manifest-out "$MANIFEST"
```

**Varsayılan `verified-only` ve sayısal `--budget-cr` gerçek yetki/fiyat kanıtı ister.** Mevcut observed tüketici bu kanıtları üretmez; bu yolda plan `draft` kalır. Bilinmeyen fiyat sıfır sayılmaz.

Aşağıdaki alternatif **açık denemedir**: yetki önceden doğrulanmamıştır ve CR tavanı uygulanmaz. Bu koşulları kabul ediyorsanız tek yeni niyet için planı hazırlayın:

```bash
.venv/bin/yorunge datasets upload plan "$ROOT" \
  --manifest "$MANIFEST" --name 'private-dataset-demo' \
  --owner-user "$OWNER_ID" --project "$PROJECT_ID" --modality VISION \
  --admission-policy explicit-attempt --unpriced \
  --config "$CFG" --state-dir "$STATE"
```

Organizasyon sahibi için `--owner-user` yerine `--owner-org` seçilir. Çıktıdaki plan ID’yi kullanın:

```bash
PLAN_ID='PLAN_UUID_FROM_OUTPUT'
.venv/bin/yorunge datasets upload review --plan-id "$PLAN_ID" --state-dir "$STATE"
```

Review, **sizin seçtiğiniz** hedef/owner/proje/ad/kök, dosya sayısı/byte, request sınırları ve maliyet riskini gösterir. Bunlar provider’ın bildirdiği kimlik veya izin değildir. Uygunsa tam digest’i kopyalayıp onaylayın; onay komutu ağda yazma yapmaz, güncel içerik ve bağlamı tekrar kontrol eder:

```bash
DIGEST='FULL_64_HEX_DIGEST_FROM_REVIEW'
.venv/bin/yorunge datasets upload approve --plan-id "$PLAN_ID" --confirm "$DIGEST" \
  --accept-unverified-authority --accept-unpriced-cost \
  --config "$CFG" --state-dir "$STATE"

.venv/bin/yorunge datasets upload start --plan-id "$PLAN_ID" \
  --config "$CFG" --state-dir "$STATE"
```

Sadece gereken acknowledgement’lar kabul edilir. Plan/onay en çok 900 saniye geçerlidir; değişmiş kaynak veya bağ eski onayla gönderilmez. TTY ilerlemesinde **taşımaya verilen byte** ve **kalıcı confirm ile onaylanan dosya/byte** ayrı görünür. JSON/NDJSON ve non-TTY’de ilerleme metni yoktur. Başarılı sonuç operation ve dataset ID ile yalnız metadata doğrulama seviyesini gösterir.

İlk yol en çok **128 dosya**, dosya başına **500.000.000 byte**, toplam **1 GiB** kabul eder. Her PUT en çok **120 saniyedir**; 500 MB için kesintisiz en az **33,34 Mbit/s** yükleme hızı gerekir. Kontrol ve bağlantı giderleri ek süre tüketir. Daha yavaş bağlantıda uzak yazma gerçekleşmiş olsa bile sonuç belirsiz kalabilir; otomatik resume yoktur. Plan, onay ve ilk çalıştırmanın 900 saniyelik pencereleri ayrı uygulanır; kalan onay süresi aktarımı tamamlamaya yetmeyebilir.

Store kotası **128 plan ve bağlı iş**, **4.096 dosya** ve **16 MiB ayrılmış payload** sınırlarından ilk dolana kadardır. Taslaklar, süresi dolan planlar ve terminal geçmiş de yer kaplar; otomatik silinmez. Bunlar bütün üst sınırlara aynı anda ulaşma garantisi değildir. `upload list` ile geçmişi inceleyin; belirsiz işi aşmak için yeni store veya ad kullanmayın. `revoke` onayı geri alır; aynı plan yeniden onaylanmaz ve geçmişi silmez.

## Aynı içerikli dosyaları bulma

İlk Platform upload yolu, farklı adlarla aynı SHA-256 içeriğini taşıyan dosyaları uzak çağrıdan önce reddeder. Yerel `inspect`/`verify` ve manifest bu adları ayrı korur. Boş dosyalar ve hardlink’ler de aynı içeriğe sahip olabilir. Manifestte hangi adların birlikte göründüğünü ağ veya credential kullanmadan bulabilirsiniz:

```sh
.venv/bin/python - "$MANIFEST" <<'PY'
import json
import sys
from pathlib import Path

groups = {}
for item in json.loads(Path(sys.argv[1]).read_bytes())["files"]:
    groups.setdefault(item["sha256"], []).append(item["path"])
print(json.dumps([names for names in groups.values() if len(names) > 1],
                 ensure_ascii=False, indent=2))
PY
```

Bu örnek yalnız ad gruplarını gösterir; dosya kopyalamaz/silmez ve manifesti değiştirmez. Aktarmak istediğiniz dosyaları kendi seçiminizle ayrı bir klasörde düzenleyip o klasör için yeni manifest ve plan üretin. Aynı içerikli bütün adları uzak tarafta korumak gerekiyorsa [P02-R2](../roadmap/tasks/p02-r2-upload-content-cardinality.md) desteği henüz açık olduğundan bu upload yolunu kullanmayın. Mevcut unknown işi yeni planla tekrar göndermeyin; aşağıdaki geçmiş/uzlaştırma yolunu izleyin.

## Kesinti ve geçmiş

`start` aynı planı tekrar göndermez. Latched pending/unknown exit5 + aynı ID, henüz arm edilmemiş veya failed/cancelled kayıt exit2, mevcut succeeded kayıt yerel başarıdır. Gönderim belirsizliğinde yeni create/plan/ad ile denemeyi tekrarlamayın. Önce yerel kaydı inceleyin; ID ilk çıktıdan önce kaybolmuşsa plan ID yeterlidir:

```bash
.venv/bin/yorunge datasets upload show --plan-id "$PLAN_ID" --state-dir "$STATE"
.venv/bin/yorunge datasets upload list --state-dir "$STATE" --output json
```

Tam accepted write grafiği ve bilinen dataset olan uygun unknown kayıt için ayrı salt okuma isteği:

```bash
OPERATION_ID='OPERATION_UUID_FROM_SHOW'
.venv/bin/yorunge datasets upload reconcile --operation-id "$OPERATION_ID" \
  --accept-unverified-read --config "$CFG" --state-dir "$STATE"
```

Bu yeni yazma hakkı veya etkili resume değildir. Kaynak dosyaları gerekmez; güncel anahtarla aynı uzak kaynak okunur. Missing receipt/ID veya etkin başka owner başarıyla doldurulmaz. Okuma retleri güvenli kaynak koduyla döner; uzak iptal sayılmaz. Yerel onayı geri almak için `upload revoke --plan-id "$PLAN_ID" --state-dir "$STATE"` kullanılır; zaten arm edilmiş istek geri çekilmiş sayılmaz.

Create cevabı yerel kayda girmeden kesildiyse dataset ID bilinmeyebilir; Platform’da private bir kaynak kalmış olabilir. Adından ID tahmin etmek veya yeni create göndermek güvenli kurtarma değildir. Yerel kaydı koruyun; Platform arayüzünde salt inceleme yapabilirsiniz. Bu yol otomatik silme veya eksik receipt’i sonradan üretme desteği sunmaz.

Aynı yerel sonuç Python’dan:

```python
from pathlib import Path
from yorunge import api

result = api.show_dataset_upload(plan_id="PLAN_UUID", state_dir=Path(".local/upload/state"))
print(result.data.operation_id, result.data.operation_status, result.data.verification_level)
```

Diğer yedi API imzası, çıktı ve hata önceliği [public sözleşmede](dataset-upload-public.md) tek yerde tutulur. `--output json|ndjson` aynı typed sonuçları verir; üst Result v1 kimliği null, gerçek kimlik summary/event/error içindedir.
