# Collect parser/import garbage before MicroPython expands into Wi-Fi heap.
import gc
gc.collect()
gc.threshold(4096)
import network
network.WLAN(network.STA_IF).active(True)
import ota_boot
ota_boot.run()
