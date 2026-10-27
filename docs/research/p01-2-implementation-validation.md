# P01-2 uygulama ve kabul kaydı

**Tarih:** 2026-10-27. **Durum:** Uygulama başladı; kabul tamamlanmadı. **Dal:** `feat/p01-2-identity-context`, ilk uygulama tabanı `d96b65e`; development tabanı `83bcd83`. Tek PR kullanıcı review'sine sunulacak; merge/yayın bu kayıtla yapılmaz.

## Belge incelemesi ve plan

Kullanıcı bütün P01-2'yi ve her adım için commit → iki ayrı yeni ajan review turu → doğrulanmış bulguları düzelt/commit akışını yetkilendirdi. Accepted ADR-0011/0012 ve binding v1 korunur. Yeni ADR gerektiren doğrulanmış karar açığı yoktur; rutin CLI/API isimleri ilgili reference içinde uygulamayla birlikte kesinleştirilir.

Root ve iki bağımsız salt okuma ajanı (`p012_document_audit`, `p012_surface_audit`; GPT-6.1 Sol/high) scope/matris, standartlar, architecture/execution/state, identity modülü, config/CLI/capability/binding, ADR'ler, araştırma ve dört iş kartını mevcut kodla karşılaştırdı. Config belgesinin boş query/fragment anlatımı düzeltildi; eski parser/Plan biçimi değiştirilmez. Guarded secret, seçili env'yi bir kez okuma, ortak bakım kilidi, no-clobber backup, reset/restore ayrımı ve default doctor'ın yan etkisizliği özel kabul noktalarıdır.

| Adım | Teslim | Durum |
|---|---|---|
| 1 | P01-2a — env/taşıyıcı/hedef kapısı | İlk uygulama/test tamam; iki review turu bekleniyor |
| 2 | P01-4a — store/migration/backup/key temeli | Doğrudan bağımlılık bekliyor |
| 3 | P01-2b — kalıcı kimlik/nesil | Doğrudan bağımlılık bekliyor |
| 4 | P01-2b — reset/identity-only restore | Adım 3 bekliyor |
| 5 | P01-2c — init/profil/proje/doctor | Önceki kabul bekleniyor |

Her adımın gerçek commit/test/review bulgusu burada kaydedilecek. Tasarım/probe sonucu ürün kabulü sayılmaz. Son kapanışta tam offline suite, lint/type/belge, wheel/sdist iki temiz kurulum, en az 30 süreç başlangıç bütçesi ve son PR head CI kanıtı gerekir. HTTP/cache/operation/uzak kimlik bu paketin teslimi değildir.

Başlangıç doğrulaması: temiz `d96b65e` üzerinde `.venv/bin/pytest -q` → **404 geçti** (3,84 s); `git fetch` sonrası development ile fark 0 geri / 3 hazırlık commit'i ileri. Kullanıcı dosyası/değişikliği bulunmadı.

## Adım 1 — İlk uygulama

Hizmet/ref/immutable gözlem taşıyıcısı ve tek seçili env okuma; strict UTF-8 1–16.384 bayt; saf `service-target-v1` normalleştirme; `api.check_credential` ve `context credential --service` sonucu eklendi. Secret public zarf/JSON'a girmez; açık kontrol hesap/yetki doğrulaması değildir. Eski Profile/Plan parser ve digest üreticisi değiştirilmedi. Subprocess guard varsayılan yollarda credential env okumalarını da reddeder; yalnız açık credential fixture modu izin verir, ağ/DB yasakları korunur.

İlk doğrulama: **460 test geçti** (4,97 s), Ruff format/lint, strict mypy (20 kaynak), 95 belge ve 6 skill/5 kart denetimi geçti. Wheel (20 üye) ve sdist (147 üye) iki ayrı temiz kurulum/köken/smoke kontrolünden geçti. 30 ayrı süreç başlangıç ölçümünün üç bütçesi de geçti; bu ölçüm güç kesintisi veya canlı auth kanıtı değildir. İki yeni review turu tamamlanmadan kart `verified` yapılmaz.

İlk ürün commit'i `41c7dba`. Başlangıç sıcak p95: help 28,196 ms / version 27,717 ms / context 97,353 ms; hedefler 500/500/200 ms (CPython 3.11.18, macOS arm64; komut başına 30 ayrı süreç).

### Adım 1 / review 1

Üç yeni bağımsız ajan (GPT-6.1 Sol/high): `p012_s1_r1_secrets` (tek okuma/taşıyıcı/sızıntı), `p012_s1_r1_target` (URL sözleşmesi/eski Plan), `p012_s1_r1_surface` (CLI/API/guard/belge). Kök ajan üç P2'yi yeniden üretti: bracketed IPvFuture'ın DNS'e çevrilmesi, Unicode Kelvin host'un parser lowercase ile ASCII'ye dönüşmesi ve `object.__getstate__` yolunda ham slotted secret açılması. Authority'nin özgün ASCII kontrolü, parantezli host'un zorunlu IPv6 doğrulaması ve güvenli `__getstate__` ile giderildi; secret okunmadan ret ve serialization regresyonları eklendi.

Guard'ın iki sabit env adıyla sınırlı kanıtı ürün kusuru sayılmadı; test yapılandırmasından özel env adları ve `os.environb` de kapsandı. Diğer doğrulanmış ürün bulgusu yok. Düzeltme sonrası **466 test**, Ruff format/lint ve strict mypy geçti. İkinci tur yeni ajanlarla bu head üzerinde yapılır.
