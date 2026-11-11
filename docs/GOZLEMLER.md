<!-- 11.11.2026'da `C:\Projeler\QuantBIST_otomasyon\gozlemler.md` dosyasından taşındı (L madde 1); tek kaynak artık bu dosya. -->
## 2026-10-28 (yarım gün: Cumhuriyet Bayramı arifesi)
- 18:30 zamanlı çalışma ağ hatasıyla düştü: `2026-10-28T18:30:01+03:00,2026-10-28T18:30:57+03:00,,failed,ConnectError: [Errno 11001] getaddrinfo failed`
- 19:09'da elle bir kez yeniden çalıştırıldı (--force yok), yarım gün verisiyle gönderildi: `2026-10-28T19:09:57+03:00,2026-10-28T19:10:13+03:00,2026-10-28,sent,`
- Sonuç: yarım günde rapor data_day = bugün ile üretildi (XU100 son kapanış 28.10.2026). Not: zamanında teslim değil (SLO 19:00 kaçtı), kök neden geçici DNS hatası.
