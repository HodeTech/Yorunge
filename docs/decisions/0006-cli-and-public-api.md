# ADR-0006: Ortak çekirdek üzerinde CLI ve Python API

**Durum:** Accepted — başlangıç tasarımı. **Tarih:** 2026-10-27.

## Bağlam

Kullanıcı hızlı rehberli başlangıç, geliştirici doğrudan komut, ekip CI çıktısı ister. Her yüzeyin ayrı iş mantığı kullanması onay, bütçe, hata ve sonuç tutarsızlığı yaratır.

## Karar

İlk yüzeyler CLI ve Python API'dir. Rehberli mod aynı kullanım senaryolarını çağırır. Açık çıktı biçimi, kararlı hata kodları ve anlaşılır insan mesajları tasarlanır. MCP daha sonra aynı çekirdeğin adaptörü olur. Büyük bir web/masaüstü arayüzü ilk teslim koşulu değildir.

## Alternatifler

Sadece sihirbaz tekrar eden işleri yavaşlatır. Sadece düşük seviyeli API yeni kullanıcıya fazla bağlam yükler. İlk aşamada tam GUI, erişim ve aktarım doğruluğu çözülmeden geliştirme yüzeyini büyütür.

## Sonuçlar

Komut ağacı görev adlarına dayanır. TTY ile çıktı formatı birbirine bağlanmaz; CI gizli prompt'ta kalmaz. UX ve başlangıç bütçesi bütün yüzeylerde sınanır. [CLI sözleşmesi](../reference/cli-contract.md).
