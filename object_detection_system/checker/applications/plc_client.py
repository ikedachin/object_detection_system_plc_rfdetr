"""OMRON FINS/UDP クライアント。

plc_monitor.py（PLC監視）と plc_test_server.py（ブリッジモード）の両方から使うため、
Django に依存しない独立モジュールとして切り出している。
"""


class PlcClient:
    """Adapter around the finscommand package (OMRON FINS/UDP)."""

    # FINSメモリエリアコード（ビットアクセス用）
    BIT_AREA_CODES = {
        "CIO": 0x30,
        "W": 0x31,
        "H": 0x32,
        "A": 0x33,
        "D": 0x02,
    }

    def __init__(self, connection_config):
        try:
            from finscommand import fins
        except ImportError as exc:
            raise RuntimeError("finscommand がインストールされていません。依存関係をインストールしてください。") from exc

        class _FinsUdpClient(fins):
            # finscommand 0.1.3 の __del__ は sock.cloase() の誤記で
            # AttributeError になるため、ここで安全にソケットを閉じる
            def __del__(self):
                sock = getattr(self, "sock", None)
                if sock is not None:
                    sock.close()

        self._client_class = _FinsUdpClient
        self.config = connection_config
        self.client = None

    def connect(self):
        host = self.config["host"]
        port = int(self.config.get("port", 9600))
        timeout = float(self.config.get("timeout", 2.0))

        dest_fins = self._fins_address(self.config.get("plc_node"), default="0.0.0")
        src_fins = self._fins_address(self.config.get("pc_node"), default="0.127.0")

        self.client = self._client_class(host, dest_fins, src_fins, timeout)
        # finscommand はポート9600固定のため、設定値で上書きする
        self.client.addr = (host, port)
        return self

    def close(self):
        if self.client is None:
            return
        try:
            self.client.sock.close()
        finally:
            self.client = None

    def read_bit(self, area, word_address, bit):
        command = self._bit_command(b"\x01\x01", area, word_address, bit)
        response = self.client.SendCommand(command)
        # レスポンス = FINSヘッダ10byte + コマンドエコー2byte + 終了コード2byte + データ
        if len(response) < 15:
            raise RuntimeError(f"PLCからのビット読取レスポンスが不正です: {response.hex()}")
        return bool(response[14])

    def write_bit(self, area, word_address, bit, value):
        command = self._bit_command(b"\x01\x02", area, word_address, bit)
        command.append(1 if int(value) else 0)
        self.client.SendCommand(command)

    def _bit_command(self, command_code, area, word_address, bit):
        command = bytearray(8)
        command[0:2] = command_code
        command[2] = self._bit_area_code(area)
        command[3:5] = int(word_address).to_bytes(2, "big")
        command[5] = int(bit)
        command[6:8] = (1).to_bytes(2, "big")
        return command

    @classmethod
    def _bit_area_code(cls, area):
        area_name = str(area or "CIO").upper()
        if area_name.startswith("E") and len(area_name) >= 2 and area_name[1:2].isalnum() and area_name not in cls.BIT_AREA_CODES:
            # EMエリアはバンク番号付き（例: E0, E1, ... EA）
            return 0x20 + int(area_name[1:], 16)
        code = cls.BIT_AREA_CODES.get(area_name)
        if code is None:
            raise RuntimeError(f"未対応のPLCメモリエリアです: {area}")
        return code

    @staticmethod
    def _fins_address(node, default):
        if node is None:
            return default
        return f"0.{int(node)}.0"
