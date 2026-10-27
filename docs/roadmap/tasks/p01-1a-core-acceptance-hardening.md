---
id: P01-1a
phase: P01
status: in_progress
size: M
depends_on: [P01-1]
capabilities: [C13]
---
# P01-1a — İlk çekirdeğin hata ve dağıtım kabulünü sağlamlaştırma

**Tarih:** 2026-10-27. **Hazırlık tabanı:** `development@9ce5204`. Kullanıcı P01-1 için ayrıntılı belge incelemesi, uygulama, her adımda commit ve iki yeni bağımsız review turu istedi. Kullanıcı bu kartı ve iki adımlı kapsamı 2026-10-27 tarihinde onayladı; uygulama bu onayla başladı.

## Kullanıcı sonucu ve mevcut eksik

P01-1'in ilk teslimi vardır ve tarihsel kabulü korunur. Amaç aynı çekirdeği yeniden yazmak değil, mevcut sözleşmenin doğrulanmış hata yollarını ve dağıtım denetimini tamamlamaktır. Hazırlıkta 131 test, format/lint/strict mypy, belge/ajan denetimi ve lock kontrolü geçti; mevcut wheel/sdist ayrı temiz ortamlara kurulabildi. Bunlar aşağıdaki yeni negatif senaryoların geçtiği anlamına gelmez.

| Bulgu | Doğrulanan davranış | Beklenen sonuç |
|---|---|---|
| F1 — YAML hata sınırı | `task: !!bool synthetic-value` API'de `KeyError`, CLI'da ham değer içeren traceback ve çıkış 1 üretiyor; bozuk diğer standart scalar tag'leri de incelenmeli | Bozuk reçete `invalid_recipe`; CLI çıkış 2, boş stdout ve tek güvenli JSON hata zarfı |
| F2 — Yerel şema | `data.manifest` TAB/ESC/DEL, hizmet URL'si DEL/C1 kontrol karakteri veya boş userinfo işareti kabul edebiliyor | Belgelenmiş kontrol karakteri ve userinfo yasağı bütün ilgili girişlerde uygulanır |
| F3 — CLI belgesi | CLI referansı uyumsuz seçimin çıkış 2 olmasını capability sorgusuna da genelliyor; sorgu gerçekte 0 + `unsupported` kayıt döndürüyor | Plan hazırlama hatası ile geçerli capability sorgusunun sonucu açık ayrılır; mevcut sorgu davranışı korunur |
| F4 — Arşiv denetimi | `../pyproject.toml`, `/pyproject.toml` ve birden çok sdist kökü ilk segment atılınca kabul ediliyor; wheel symlink metadata'sı incelenmiyor | Orijinal üye adı ve türü kurulumdan önce denetlenir; güvensiz yol, uygunsuz üye türü ve kök reddedilir |
| F5 — Kanıt akışı | Kanonik doğrulama komutu JSONL'yi stdout'a basıyor; belirtilen `dist/verification.jsonl` dosyasına yazmıyor | Yeniden çalıştırılabilir komut kayıt dosyasını gerçekten üretir; tarihsel kayıt ile yeni kanıt ayrıdır |
| F6 — Belge sırası | Eski kabul kaydındaki sonraki iş cümlesi güncel state/credential bağımlılık sırasını yansıtmıyor | Tarihsel sonuç silinmeden etkin iş için current/kart tek kaynak olur |

## Giren ve girmeyen kapsam

Giren: mevcut YAML/TOML/Plan doğrulamasının güvenli hata sınırı; dosya yolu ve hizmet URL şemalarının belgelenen kuralları; CLI/Python hata ve capability sözleşmesi; wheel/sdist üye denetimi; ilgili anlamlı negatif testler; kanonik komutlar ve teslim kanıtı.

Görevler, araç seçimi, EVREN hizmetleri ve ortamlar mevcut offline alt kümeyle sınırlıdır. HTTP seçimi P01-5a, env secret çözümleme P01-2a, kalıcı kimlik/state P01-4a/P01-2b, capability cache ve yürütme geçerliliği P01-3'tedir. Bunlar bu kartta ertelenen eksikler veya yeniden açılan kararlar değildir. Gerçek EVREN erişimi, eğitim, yayın ve Master aktarımı yapılmaz.

## Bağımlılıklar ve kararlar

P01-1 ilk teslimi [PR #1](https://github.com/HodeTech/Yorunge/pull/1), [kabul kaydı](../../research/p01-core-validation.md) ve [ADR-0008](../../decisions/0008-offline-core-stack.md) ile kanıtlıdır. Ortak yüzey kararı [ADR-0006](../../decisions/0006-cli-and-public-api.md), dar iş/kanıt disiplini [ADR-0010](../../decisions/0010-roadmap-readiness-and-agent-skills.md) ile belirlenmiştir.

Hazırlık incelemesinde yeni teknoloji, varsayılan, güven sınırı veya ürün kapsamı kararı gerekmemiştir; yeni ADR önerilmiyor. Kullanıcı bu kartın kapsam/adımlarını onayladı; başlangıç için açık karar kalmadı. Uygulama yeni bir mimari karar gerektirirse ilgili belge Proposed hazırlanır ve bağımlı koddan önce kullanıcı onayı alınır. Mevcut hatalı girdilerin kontrollü reddi uyumluluk daralması olarak referansta belirtilir; geçerli v1 dosyaları ve sonuç biçimi korunur.

## Sözleşme ve uygulama sınırı

Kanonik sözleşmeler [config](../../reference/configuration.md), [CLI](../../reference/cli-contract.md), [Python](../../standards/python.md), [güvenlik](../../standards/security.md), [test](../../standards/testing.md) ve [paket doğrulama komutlarıdır](../../../CONTRIBUTING.md#doğrulama-seçimi). Mevcut dosya adaptörü ve domain modelleri düzeltilir; iş mantığı CLI'ya kopyalanmaz. Parser istisnaları yalnız gerçek dış girdi sınırında güvenli hataya çevrilir; bütün uygulamada geniş exception yutma kullanılmaz.

**Adım 1 — Parser/şema ve kullanıcı sözleşmesi:** F1/F2/F3 için önce mevcut hatayı yakalayan gerçek dosya/API/CLI senaryolarını ekle; YAML constructor hata sınırını düzelt; manifest ve URL için kontrol karakteri/userinfo kurallarını uygula. Geçerli Unicode yollar, standart geçerli YAML, hizmet/araç/ortam ayrımı ve offline davranış korunur. İlgili referansı aynı commit'te güncelle.

**Adım 2 — Dağıtım ve kapanış kanıtı:** Adım 1'in iki review turu bittikten sonra F4/F5/F6'yı tamamla. Gerçek sentetik ZIP/tar arşivleriyle orijinal üye adı, kök ve dosya türünü sınayan testler yaz; geçerli üretilmiş arşivleri ve iki temiz kurulumu doğrula. Kanonik JSONL kayıt komutunu düzelt; yeni test/build/başlangıç sonucunu tarihsel kabulden ayrı kaydet ve current/faz/kart bağlantılarını güncelle.

Her adımda: uygulama + anlamlı doğrulama → commit → birinci tur yeni bağımsız review ajanları → doğrulanmış bulguları düzelt ve commit → ikinci tur başka yeni bağımsız review ajanları → doğrulanmış bulguları düzelt ve commit. Turlar kod/doğruluk/sır/hata, sözleşme/UX ve ilgili dağıtım/kaynak sınırlarını kapsar. Reviewer tercihi tek başına kusur sayılmaz. Son düzeltme yeni risk yaratırsa ilgili kontrol ve odak review tekrarlanır; çözümsüz doğrulanmış bulgu sonraki adıma bırakılmaz.

## Kabul

1. Bozuk standart YAML scalar tag'leri ham `KeyError`/`IndexError`/`AttributeError`/`OverflowError`, traceback veya girdi sızıntısı üretmez; boş int/float, geçersiz bool/timestamp ve taşan sexagesimal float örnekleri kapsanır. API kararlı `YorungeError`; gerçek konsol JSON çağrısı çıkış 2, boş stdout, tek `invalid_recipe` stderr kaydı verir. Geçerli reçete desteği korunur.
2. Manifest ve hizmet URL'sinde C0 (`U+0000–U+001F`), DEL (`U+007F`) ve C1 (`U+0080–U+009F`) kontrol karakterleri reddedilir; URL userinfo işareti boş olsa da reddedilir. Gerçek TOML/YAML/kayıtlı Plan sınırı ve geçerli Unicode/IPv6 örnekleri kanıtlıdır. Yerel girdi reddi uzak hedefin güvenilirliğini doğrulamaz.
3. CLI ve Python geçerli capability sorgusunda uyumsuzluğu `unsupported` kayıtla bildirir; plan hazırlama uygun kontrollü hatayla reddeder. Doküman ve integration testi bu ayrımı aynı biçimde anlatır.
4. Arşiv denetimi kök atılmadan önce mutlak/traversal yolları, uygunsuz kökleri, arşiv linklerini ve normal dosya/dizin dışındaki üyeleri reddeder. Yinelenen veya kanonik olmayan adlar belirsiz kurulum üretmez. Gerçek wheel/sdist izin listesi geçer, kaynak/import kökeni depo dışındaki iki temiz kurulumda doğrulanır.
5. Kanonik komut arşiv adı, SHA-256, üye sayısı ve gerçek temiz kurulum sonucunu `dist/verification.jsonl` dosyasına bırakır. Build çıktısı Git'e girmez; arşiv kendi hash'ini kaynak dosyasına gömmez.
6. İki adımın ayrı commit ve iki yeni bağımsız review turu kaydı vardır; doğrulanmış bulgular kapatılmıştır. Tam yerel kapılar, güncel başlangıç bütçeleri ve belge uyumu kanıtlıdır. PR development hedefli kullanıcı review'sine sunulur; bu görevde otomatik merge yapılmaz.

## Doğrulama

Adım 1'de gerçek dosya ve subprocess negatif testleri, ilgili unit/contract/integration paketi, Ruff format/lint, strict mypy ve belge kontrolü çalıştırılır. Adım 2'de sentetik arşiv negatif/pozitif testleri, tam pytest, belge/ajan denetimi, lock kontrolü, wheel/sdist build, arşiv denetimi, iki ayrı temiz kurulum ve [başlangıç bütçeleri](../../standards/performance.md#başlangıç-bütçeleri) çalıştırılır. En az 30 ayrı süreç, üç ısınma, ilk süreç ve p95/ortam kaydı gerekir; eşik gevşetilmez.

İnceleme ajanları readonly çalışır; her turun kapsamı, taban commit'i, doğrulanmış/reddedilmiş bulgusu ve düzeltme commit'i teslimde kaydedilir. Bir ajan kullanılması bütün yetenek veya canlı hizmet doğrulaması sayılmaz. Tekrar kontrolleri değişen sınır ve kalan riskle gerekçelendirilir. Dış CI sonucu PR açıldıktan sonra son head üzerinde ayrıca okunur; bu hazırlıkta CI çalıştı denmez.

## Teslim kaydı

Adım 1 ve iki review turundaki düzeltmeler tamamlandı; 345 test geçti. Adım 2 uygulandı; 55 gerçek sentetik arşiv senaryosu dahil 400 test, build/iki temiz kurulum ve başlangıç bütçeleri geçti. Adım 2 review turları ve PR henüz tamamlanmadı. Hazırlık probe'ları düzeltme kabulü değildir.

| Adım / tur | İncelenen commit | Kapsam ve sonuç |
|---|---|---|
| 1 / uygulama | `8ae0fc5` | Parser/şema ve CLI referansı; 338 test geçti, lint/type/belge temiz |
| 1 / review 1 | `8ae0fc5` | İki yeni bağımsız ajan: girdi/hata güvenliği (GPT-6.1 Sol xhigh), sözleşme/UX (GPT-6.1 Sol high). Tek doğrulanmış P2: yanlış türde `!!map`/`!!set` düğümü TypeError veya sessiz boş mapping dönüşümü üretebiliyor. `f05ab2d` düğüm türü denetimi ve gerçek API/CLI regresyonlarıyla giderdi; ikinci tur bu düzeltmeyi doğruladı |
| 1 / review 2 | `f05ab2d` | Başka iki yeni ajan: parser/güvenlik (GPT-6 Astra high), sözleşme/UX (GPT-6.1 Sol high). Tek doğrulanmış P2: timestamp scalar tag'i `{=: ...}` mapping'iyle TypeError üretiyor. `1e2df18`/`96755da` scalar düğüm türü denetimi ve gerçek API/CLI regresyonlarıyla giderdi; aynı reviewer'ın odak kapanışında 256 varyant ve altı gerçek CLI timestamp deneyi kontrollü reddedildi, geçerli scalar girdiler korundu, açık doğrulanmış bulgu kalmadı |
