# P02 hesap kabulü için yerel hazırlık

**Tarih:** 2026-10-31. **Durum:** Hazırlık yönergesi; aşağıdaki dosya oluşturma ve yerel state komutları uzak çağrı yapmaz. Discovery uygulama/kabul durumu [P02-0 kaydındadır](research/p02-0-implementation-validation.md). Gerçek pilot yalnız hazırlanmış kapsam üzerinden yürütülür; anahtar değerleri sohbet/PR/kanıt dosyasına yazılmaz.

## Gerekenler

Kendi yetkin olan EVREN hesabının **LLM anahtarı** ilk bağımsız kol için yeterlidir. Platform kimlik/org/proje kabulünü ayrıca sınamak için **Platform API anahtarı** gerekir; browser JWT’si veya oturum cookie’si gerekmez. Mevcut kullanıcı hesabında üç uç ve ayrı seçili-proje consumer kabulü kayıtlıdır; bu gelecekteki her key/hedef için erişim veya auth/principal garantisi değildir. Şart kabulü gerekiyorsa kullanıcı EVREN arayüzünde kendisi yapar; pilot POST accept çağırmaz.

Account/project ID’lerini bilmiyorsan boş bırakabilirsin; ilk LLM keşfi bunları gerektirmez. Platform’da otomatik yeni hesap/proje oluşturulmaz. Platform için bildiğin hesap/proje ID’lerini aşağıda girebilirsin; normal discovery’nin okuduğu config profiline ve araştırma için scope dosyasına yazılır. Account ID’nin user mı organizasyon mu olduğu belli değilse boş bırak; isim veya model owner’dan türetme. İlk proje otomatik seçilmez. LLM hesabını Platform ID’siyle eşleştirmek için bu bilgiler kullanılmaz.

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
for key, value in scope.items():
    if value is not None:
        config += f'{key} = {json.dumps(value, ensure_ascii=False)}\n'
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

## Hazırlıktan normal discovery’ye

`scope.json` araştırma pilotunun girdisidir; normal CLI/Python bu dosyayı okumaz. Yukarıdaki yeni hazırlık bloğu dolu account/project tercihlerini `config.toml` içindeki `profiles.pilot` tablosuna da yazar. Önceki hazırlıkla dosya oluşturduysan mevcut `[profiles.pilot]` tablosuna bildiğin değerleri TOML string olarak ekle; ikinci bir tablo başlığı oluşturma, bilmediğin alanı ekleme:

```toml
account_id = "known-platform-account-id"
project_id = "selected-platform-project-id"
```

Proje tercihini mevcut CLI ile de kaydedebilirsin: `.venv/bin/yorunge context set-project PROJECT_ID --config .local/p02-pilot/config.toml`. Tek çağrıda değiştirmek için `context discover` komutuna `--project PROJECT_ID` eklenir; LLM açık project override kabul etmez. Yerel hesap tercihi yalnız config profilindedir; bildirilen kullanıcı/org ID’sinden türetilmez. Tercih doğrulanmış kimlik veya izin sayılmaz.

Anahtarı `credentials.json` dosyasından **yalnız seçili hizmetin çocuk sürecine** aktarıp aşağıdaki bloğu çalıştır. Platform için yalnız `service = "evren-platform"` yap; profil projesi varsa detail GET’i de yapılır. Anahtarı shell argümanına/export komutuna yazma. Bu adım gerçek salt okunur ağ çağrısı yapar; önceki hazırlık ve state init adımları yapmaz:

```sh
.venv/bin/python - <<'PY'
import json
import os
import subprocess
import sys
from pathlib import Path

service = "evren-llm"
reference = {"evren-llm": "PILOT_LLM_KEY", "evren-platform": "PILOT_PLATFORM_KEY"}[service]
root = Path('.local/p02-pilot')
try:
    credentials = json.loads((root / 'credentials.json').read_text(encoding='utf-8'))
except (OSError, ValueError):
    raise SystemExit('Credential hazırlığı okunamadı; içerik gösterilmedi.') from None
value = credentials.get(reference) if type(credentials) is dict else None
if type(value) is not str or not value:
    raise SystemExit('Seçili hizmet anahtarı hazırlanmamış; ağ çağrısı yapılmadı.')
env = dict(os.environ)
for name in ('PILOT_LLM_KEY', 'PILOT_PLATFORM_KEY'):
    env.pop(name, None)
env[reference] = value
result = subprocess.run(
    [sys.executable, '-m', 'yorunge', 'context', 'discover', '--service', service,
     '--config', str(root / 'config.toml'), '--state-dir', str(root / 'state'),
     '--output', 'json'],
    env=env,
    check=False,
)
raise SystemExit(result.returncode)
PY
```

Çağıran terminalin ortamı değişmez; komut ve hata kodu çocuktan gelir. Ürün config’i/discovery credential dosyasını doğrudan okumaz; tek env snapshot kuralı korunur. Dosya içeriklerini `cat`, ekran görüntüsü veya sohbetle paylaşma. Ürünü başka terminalden doğrudan çalıştırmak için ilgili env’yi o terminalde ayrıca güvenli gizli girişle hazırlamak gerekir; başka terminalde `export` yapmak mevcut sürecin ortamını değiştirmez.

## Salt okunur kabulün kapsamı

Normal discovery negatif kontrol yapmaz. Aşağıdaki invalid-key deneyi yalnız ayrıca yetkili opsiyonel auth araştırmasıdır; dar gözlem tesliminin kapanış önkoşulu değildir.

| Hizmet | Pozitif çağrı tavanı | Auth sözleşmesi eksikse, yalnız ayrı yetkili opsiyonel araştırmada endpoint başına kontrol | Pilot toplam tavanı |
|---|---|---|---|
| Platform | me/orgs/projects/seçili project için ≤4 GET, her biri en çok 2 attempt | Her kullanılan endpoint + ilgili parametre kapsamı için 1 iyi biçimli, rastgele invalid-key GET; retry yok | ≤8 GET/12 attempt/4 MiB; toplam 30 s |
| LLM | terms/status için 1 GET, en çok 2 attempt | Aynı endpoint’te 1 iyi biçimli invalid-key GET; retry yok | ≤2 GET/3 attempt/1 MiB; toplam 30 s |

Tavanlar hedef çağrı sayısı değildir; gerekmedikçe istek yapılmaz. Kontrol anahtarı sağlayıcının doğrulanmış sözdizimi/önek/uzunluğunu taşır, yerelde rastgele üretilir ve sağlayıcı tarafından verilmiş değildir. Biçim bilinmiyorsa malformed tahminle auth kanıtı üretilmez. 401 veya açıkça invalid-key anlamı doğrulanmış 403 aranır; terms/permission 403’ü yeterli değildir. Kontrol anahtarı registry’ye yazılmaz. Auth kanıtı başka endpoint/parametre/hedefe aktarılmaz.

Upload, inference, export hazırlama, key üretme, şart kabulü, kaynak rezervasyonu ve uzak silme yoktur. Salt okuma uçlarının fiyatı veya erişimi bilinmiyorsa sıfır maliyet varsayılmaz; ücretli olduğu saptanan çağrı yapılmaz. 401/403/429, yanlış endpoint, schema/target farkı veya deadline/boyut sınırında durulur; beklenen negatif kontrol reddi ayrı oracle’dır. Ham kullanıcı cevabı/header/key/signed URL repoya girmez. Hizmet başına gözlenen alanlar, auth belirsizliği ve kontrol sonucu maskeli kanıtta ayrı kaydedilir.

## Platform sözleşme kapısını açmak

**1 Kasım güncel kapsam:** Aşağıdaki destek talebi özgün doğrulanmış kimlik/bağ ihtiyacı P02-R1 için yararlıdır. Accepted ADR-0022 ile bu bilgi dar unverified gözlem tesliminin önkoşulu olmaktan çıkarıldı. Bu bölüm önceki dış kapının hazırlığını korur; yeni kullanıcı bu belgeyle key/resource yaratmaya veya yetkisiz pilot yapmaya yönlendirilmez.

Account/project ID’si bulmak bu kapıyı kapatmaz. Kullanıcının paylaştığı “Platform API ile Veri Seti Entegrasyonu” kılavuzu kökü, X-API-Key başlığını, evren_ önekini ve dataset işlemlerini anlatır. “Çoğu yanıt” ifadesi endpoint başına kapalı şema değildir; dataset items next_cursor kuralı organizations/projects listelerine aktarılamaz. Tek HTTP200 de principal/izin veya anahtar doğrulaması kanıtı değildir.

Kılavuzda veya sağlayıcının dokümanlarında **OpenAPI**, **Swagger**, **API referansı** aramasıyla bulunan resmî JSON/YAML bağlantısı yeterlidir. Erişilebilir böyle bir dosya yoksa sağlayıcı desteğine şu talep iletilebilir; Yörünge bu mesajı kullanıcı adına göndermez:

> Yörünge entegrasyonunda yalnız salt okunur hesap/proje keşfi yapıyoruz. X-API-Key ile GET /api/v1/auth/me, /api/v1/organizations, /api/v1/projects ve /api/v1/projects/{id} desteğini tanımlayan güncel OpenAPI/Swagger JSON/YAML veya resmî endpoint sözleşmesini rica ediyoruz. Gerekli bilgiler: minimum yanıt alanları ve success/data zarfı; principal/user/account/organization/project ID alanlarının anlamları ve ilişkileri; liste pagination/tamlık kuralları; bu uçlar için API key scope’ları, geçerli key sözdizimi/uzunluğu ve invalid-key401/403 ayrımı. Anahtar veya kişisel veri içermeyen örnekler yeterlidir.

Destek yanıtı veya resmî bağlantı paylaşılır; anahtar değeri, gerçek hesap JSON’u, Authorization/Cookie başlıkları, browser JWT veya HAR dosyası paylaşılmaz. Kişisel veri içeren cevaptan şema tahmin edilmez. Yeni kanıt hedef/hizmet/endpoint/parametre kapsamıyla P02-R1 araştırma kaydına bağlanır; doğrulanmış kimlik/bağ için gereken ek varyant ve oracle’lar kendi işinde tanımlanır. Mevcut unverified Platform gözlemi zaten uygulanmıştır; gerekli yeni tasarım kararı çıkarsa kullanıcı ADR onay akışı korunur.


## Sonraki davranış araştırması — 2026-11-01

Kullanıcı anahtarıyla [ilk üç uç ve ayrı seçili-proje consumer kabulü](research/p02-platform-reverse-engineering.md#seçili-proje-canlı-kabulü--ayrı-koşu) tamamlandı. Ayrı koşular key 200/no-key 401 davranışı ve gerçek decoder predikatlarını gösterir; invalid-key/principal/permission/tamlık garantisi değildir. [ADR-0022](decisions/0022-observed-platform-consumer-contract.md) 2026-11-01 kullanıcı onayıyla Accepted; strict tüketilen alanlar ve mevcut literal/yapısal/byte kontrolleri nihai dar gözlem sözleşmesidir. Kullanıcının kendi private test projesi yalnız Git dışındaki girdiden kullanıldı; gerçek ID/key/raw/PII yayımlanmadı. Secret sohbetle paylaşılmaz, yeni key/proje ajan tarafından oluşturulmaz. Son kaynak/review/kurulum/M5 ve üç ortam PR CI kabulü [paket kapanışında](research/p02-0-implementation-validation.md#pr-12-son-kaynak-ci-ve-paket-kapanışı) tamamdır; PR #12 / 9f30fd2 ile development’a teslim edildi; [merge/CI kaydı](research/p02-0-implementation-validation.md#development-merge-kapanışı) günceldir.
