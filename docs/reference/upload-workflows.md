# Private dataset aktarımı

**Tarih:** 2026-11-03. **Durum:** P02-2t.3 çalışma dalındaki kullanıcı akışı; iki fresh kod turu ve üst c native/kurulum/CI/ayrı canlı kabulü henüz kapanmadı. [Kesin public sözleşme](dataset-upload-public.md), [güncel durum](../roadmap/current.md).

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

Aynı yerel sonuç Python’dan:

```python
from pathlib import Path
from yorunge import api

result = api.show_dataset_upload(plan_id="PLAN_UUID", state_dir=Path(".local/upload/state"))
print(result.data.operation_id, result.data.operation_status, result.data.verification_level)
```

Diğer yedi API imzası, çıktı ve hata önceliği [public sözleşmede](dataset-upload-public.md) tek yerde tutulur. `--output json|ndjson` aynı typed sonuçları verir; üst Result v1 kimliği null, gerçek kimlik summary/event/error içindedir.
