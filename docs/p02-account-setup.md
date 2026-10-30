# P02 hesap kabulü için yerel hazırlık

**Tarih:** 2026-10-31. **Durum:** Hazırlık yönergesi; aşağıdaki dosya oluşturma ve yerel state komutları uzak çağrı yapmaz. Discovery uygulama/kabul durumu [P02-0 kaydındadır](research/p02-0-implementation-validation.md). Gerçek pilot yalnız hazırlanmış kapsam üzerinden yürütülür; anahtar değerleri sohbet/PR/kanıt dosyasına yazılmaz.

## Gerekenler

Kendi yetkin olan EVREN hesabının **LLM anahtarı** ilk bağımsız kol için yeterlidir. Platform kimlik/org/proje kabulünü ayrıca sınamak için **Platform API anahtarı** gerekir; browser JWT’si veya oturum cookie’si gerekmez. Platform API key’in bu endpoint’lere erişebildiği henüz doğrulanmadı; bunu başarılı kabul gibi göstermeyeceğiz. Şart kabulü gerekiyorsa kullanıcı EVREN arayüzünde kendisi yapar; pilot POST accept çağırmaz.

Platform için bildiğin hesap/proje ID’lerini aşağıdaki scope dosyasına girebilirsin. Account ID’nin user mı organizasyon mu olduğu belli değilse boş bırak; isim veya model owner’dan türetme. İlk proje otomatik seçilmez. LLM hesabını Platform ID’siyle eşleştirmek için bu bilgiler kullanılmaz.

## Dosyaları güvenle hazırla

Repo kökünde, yeni bir terminalde şu bloğu çalıştır. Anahtarlar gizli girişle istenir; ekrana veya komut geçmişine yazılmaz. İki anahtardan hazır olmayanı boş bırakabilirsin. Dosyalar Git dışında `.local/p02-pilot/` altında, dizin0700/dosya0600 izinleriyle oluşturulur. Mevcut dosya ezilmez; bir dosya zaten varsa bloğu tekrar çalıştırmadan mevcut hazırlığı kontrol et.

```sh
python3 - <<'PY'
import getpass
import json
import os
from pathlib import Path

os.umask(0o077)
root = Path('.local/p02-pilot')
if Path('.local').is_symlink() or root.is_symlink():
    raise SystemExit('Hazırlık dizini symlink olamaz.')
root.mkdir(parents=True, exist_ok=True)
root.chmod(0o700)
files = [root / name for name in ('config.toml', 'credentials.json', 'scope.json')]
if any(path.exists() or path.is_symlink() for path in files):
    raise SystemExit('Hazırlık dosyası zaten var; hiçbir dosya değiştirilmedi.')
values = {}
for name, prompt in (
    ('PILOT_LLM_KEY', 'LLM API anahtarı (yoksa boş): '),
    ('PILOT_PLATFORM_KEY', 'Platform API anahtarı (yoksa boş): '),
):
    value = getpass.getpass(prompt)
    if value:
        values[name] = value
if not values:
    raise SystemExit('Anahtar girilmedi; dosya oluşturulmadı.')
scope = {
    'account_id': getpass.getpass('Bilinen Platform account ID (yoksa boş): ').strip() or None,
    'project_id': getpass.getpass('Seçilen Platform project ID (yoksa boş): ').strip() or None,
}
config = '''schema_version = 1
active_profile = "pilot"
[profiles.pilot]
platform_url = "https://api.ssyz.org.tr/api/v1"
llm_url = "https://evren-llmapi.ssyz.org.tr/v1"
platform_key_env = "PILOT_PLATFORM_KEY"
llm_key_env = "PILOT_LLM_KEY"
'''
for path, content in zip(files, (config, json.dumps(values), json.dumps(scope))):
    with path.open('x', encoding='utf-8') as target:
        target.write(content + '\n')
print('Hazırlık dosyaları oluşturuldu; içerikleri gösterilmedi.')
PY
```

Ardından ayrı yerel store’u açıkça oluştur:

```sh
.venv/bin/yorunge state init --state-dir .local/p02-pilot/state
```

Başka terminalde `export` yapmak, çalışan ajanın ortamına aktarılmaz. Bu nedenle `credentials.json` yalnız pilotu başlatan yerel kompozisyon tarafından okunup ilgili **çocuk sürecin env’sine** aktarılacaktır. Ürün config’i veya discovery doğrudan bu dosyayı okumaz; ürünün tek env snapshot kuralı korunur. Dosya içeriklerini `cat`, ekran görüntüsü veya sohbetle paylaşma; yalnız dosyaların hazır olduğunu ve varsa özel konumunu bildir. Bu hazırlık sırasında ağ çağrısı yapılmaz.

## Salt okunur kabulün kapsamı

| Hizmet | Pozitif çağrı tavanı | Auth sözleşmesi eksikse endpoint başına kontrol | Pilot toplam tavanı |
|---|---|---|---|
| Platform | me/orgs/projects/seçili project için ≤4 GET, her biri en çok2 attempt | Her kullanılan endpoint + ilgili parametre kapsamı için1 iyi biçimli, rastgele invalid-key GET; retry yok | ≤8 GET/12 attempt/4 MiB; toplam30 s |
| LLM | terms/status için1 GET, en çok2 attempt | Aynı endpoint’te1 iyi biçimli invalid-key GET; retry yok | ≤2 GET/3 attempt/1 MiB; toplam30 s |

Tavanlar hedef çağrı sayısı değildir; gerekmedikçe istek yapılmaz. Kontrol anahtarı sağlayıcının doğrulanmış sözdizimi/önek/uzunluğunu taşır, yerelde rastgele üretilir ve sağlayıcı tarafından verilmiş değildir. Biçim bilinmiyorsa malformed tahminle auth kanıtı üretilmez. 401 veya açıkça invalid-key anlamı doğrulanmış403 aranır; terms/permission403’ü yeterli değildir. Kontrol anahtarı registry’ye yazılmaz. Auth kanıtı başka endpoint/parametre/hedefe aktarılmaz.

Upload, inference, export hazırlama, key üretme, şart kabulü, kaynak rezervasyonu ve uzak silme yoktur. Salt okuma uçlarının fiyatı veya erişimi bilinmiyorsa sıfır maliyet varsayılmaz; ücretli olduğu saptanan çağrı yapılmaz. 401/403/429, yanlış endpoint, schema/target farkı veya deadline/boyut sınırında durulur; beklenen negatif kontrol reddi ayrı oracle’dır. Ham kullanıcı cevabı/header/key/signed URL repoya girmez. Hizmet başına gözlenen alanlar, auth belirsizliği ve kontrol sonucu maskeli kanıtta ayrı kaydedilir.
