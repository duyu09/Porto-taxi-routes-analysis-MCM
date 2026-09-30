# Nhận dạng mô hình di chuyển và tối ưu hóa lộ trình động dựa trên dữ liệu quỹ đạo taxi

## Ngôn ngữ

[**繁體中文**](./README.md) | [**English**](./README.en.md) | [**Tiếng Việt**](./README.vi.md)

> Nội dung dưới đây được dịch bằng mô hình GPT-5.6 và đã được hiệu đính thủ công. Tuy nhiên, sai sót vẫn có thể xảy ra. Trong trường hợp có bất kỳ điểm nào không rõ ràng hoặc có sự khác biệt về cách hiểu, vui lòng lấy phiên bản tiếng Trung Phồn thể làm bản tham chiếu chính thức.

## Tổng quan

Dự án này nghiên cứu dữ liệu quỹ đạo taxi tại thành phố Porto, Bồ Đào Nha, nhằm nhận dạng các mô hình di chuyển từ quá trình chuyển động của phương tiện, đồng thời đưa nhu cầu đô thị và trạng thái giao thông đường bộ vào bài toán lập kế hoạch lộ trình. Thông qua mô hình thống kê có khả năng diễn giải, nghiên cứu mô tả nhu cầu đi lại trong đô thị và trạng thái vận hành của mạng lưới đường bộ, đồng thời khảo sát lựa chọn lộ trình theo các mục tiêu khác nhau từ hai góc nhìn: hiệu quả di chuyển của hành khách và cơ hội đón khách tiềm năng của tài xế. Nghiên cứu được triển khai theo chuỗi “**mô tả quỹ đạo → nhận dạng mô hình → phân tích nhu cầu → tối ưu hóa lộ trình**”: trước tiên, các điểm định vị rời rạc được chuyển đổi thành mô tả chuyến đi có thể phân tích; tiếp theo, các đặc trưng di chuyển tương ứng với những hình thức đón khách khác nhau được nhận dạng; sau đó, phân bố nhu cầu theo thời gian và không gian được mô tả; cuối cùng, các mô hình lựa chọn lộ trình từ góc nhìn hành khách và tài xế được xây dựng.

**Từ khóa:** Nhận dạng mô hình di chuyển｜Phân tích nhu cầu đô thị｜Tối ưu hóa lộ trình động

📄 [**Đọc toàn bộ bài dự thi tại đây**](202602077-完整论文.pdf)

## Cấu trúc kho mã nguồn

```text
.
├── README.md
├── LICENSE
├── 202602077-完整论文.pdf     # Bài dự thi
├── ds_code/                  # Mã mô hình hóa
├── outputs/                  # Kết quả phân tích
└── images/                   # Hình ảnh trong bài báo và dự án
```

## Khung nghiên cứu

Dữ liệu quỹ đạo taxi đồng thời chứa thông tin ở ba cấp độ: chuyến đi, nhu cầu và mạng lưới đường bộ:

- **Cấp độ chuyến đi:** một chuyến đi diễn ra như thế nào, kéo dài bao lâu và phương tiện di chuyển theo lộ trình ra sao.
- **Cấp độ nhu cầu:** chuyến đi phát sinh từ đâu, hướng đến đâu và thay đổi như thế nào theo từng khoảng thời gian.
- **Cấp độ mạng lưới đường bộ:** phương tiện đi qua những tuyến đường nào, và các tuyến đường đó có điều kiện giao thông cũng như cơ hội đón khách như thế nào.

Ba cấp độ này có mối liên hệ chặt chẽ với nhau. Mô tả chuyến đi cung cấp cơ sở cho việc nhận dạng mô hình, phân bố điểm đi và điểm đến hình thành cấu trúc nhu cầu đô thị, còn thông tin vận hành lịch sử trên đường hỗ trợ việc xây dựng chi phí lộ trình.

<img src="./images/Fig01.svg" style="width:60%" />

*Quy trình nghiên cứu từ phân tích quỹ đạo đến nhận dạng mô hình di chuyển và tối ưu hóa lộ trình.*

## Mô tả quỹ đạo và nhận dạng mô hình di chuyển

### Từ điểm định vị đến mô tả chuyến đi

Quỹ đạo thô là một tập hợp các điểm định vị được sắp xếp theo thời gian. Để phân tích hành vi di chuyển, cần chuyển đổi các điểm này thành những mô tả chuyến đi có ý nghĩa rõ ràng, chẳng hạn như quãng đường di chuyển, thời gian kéo dài, tốc độ trung bình và hình dạng lộ trình.

Giả sử một quỹ đạo gồm $n$ điểm định vị, khoảng thời gian lấy mẫu giữa hai điểm liên tiếp là $\Delta t$, và $d_H$ biểu diễn khoảng cách trên bề mặt cầu. Khi đó, thời lượng chuyến đi và tổng quãng đường có thể được biểu diễn như sau:

$$D=(n-1)\Delta t,\qquad L=\sum_{j=1}^{n-1}d_H(p_j,p_{j+1}),\qquad V=\frac{L}{D}.$$

Khoảng cách và thời gian mô tả quy mô của chuyến đi, trong khi hình dạng lộ trình bổ sung thông tin về sự khác biệt trong cách thức di chuyển. Ví dụ, cùng một điểm đi và điểm đến có thể tương ứng với các mức độ đi vòng khác nhau; tương tự, những chuyến đi có quãng đường gần giống nhau vẫn có thể có thời gian di chuyển khác nhau do điều kiện đường sá. Vì vậy, hành vi di chuyển cần được mô tả đồng thời từ nhiều góc độ.

### Nhận dạng xác suất của mô hình di chuyển

Nghiên cứu này xem các chuyến gọi taxi qua điện thoại, đón khách tại điểm taxi và đón khách ven đường là những mô hình di chuyển khác nhau. Cốt lõi của bài toán nhận dạng là sử dụng các đặc trưng về thời gian, không gian và hình thái di chuyển của chuyến đi để ước lượng xác suất chuyến đi thuộc về từng mô hình.

Gọi $x$ là mô tả chuyến đi và $f_k(x)$ là điểm số mà mô hình gán cho mô hình thứ $k$. Khi đó, có thể sử dụng Softmax để chuyển đổi điểm số thành xác suất:

$$\Pr(y=k\mid x)=\frac{\exp(f_k(x))}{\sum_{\ell=1}^{K}\exp(f_\ell(x))},\qquad \hat y=\arg\max_{1\leq k\leq K}\Pr(y=k\mid x).$$

Phương pháp mô hình hóa này cho phép nhiều loại thông tin cùng ảnh hưởng đến kết quả phân loại, đồng thời có thể mô tả các mối quan hệ phi tuyến. Ví dụ, thời gian và vị trí có thể cùng tác động đến hình thức đón khách; nếu chỉ xem xét riêng từng yếu tố thì không đủ để giải thích đầy đủ mô hình di chuyển.

### Giải thích mô hình

Nhận dạng mô hình di chuyển không chỉ cần trả lời “thuộc loại nào”, mà còn phải giải thích “những thông tin nào ảnh hưởng đến kết quả dự đoán”. Nghiên cứu này sử dụng tư tưởng giải thích cộng tính của SHAP, phân rã một dự đoán thành đầu ra cơ sở và phần đóng góp của từng đặc trưng:

$$f(x)=\phi_0+\sum_{j=1}^{m}\phi_j.$$

Trong đó, $\phi_0$ biểu thị đầu ra cơ sở, còn $\phi_j$ biểu thị mức đóng góp của đặc trưng thứ $j$ đối với dự đoán. Cách phân rã này giúp hiểu cách mô hình kết hợp nhiều loại thông tin khác nhau. Tuy nhiên, nó chỉ phản ánh các mối quan hệ thống kê trong mô hình và không nên được diễn giải trực tiếp như quan hệ nhân quả.

## Cấu trúc không gian - thời gian của nhu cầu đô thị

### Luồng OD

Mối liên hệ giữa điểm đi và điểm đến tạo thành quan hệ OD. Bằng cách chia khu vực nghiên cứu thành các đơn vị không gian và tổng hợp chuyến đi theo từng khoảng thời gian, có thể xây dựng ma trận OD theo thời gian:

$$F_{ab}^{(r)}=\sum_{i=1}^{N}\mathbf{1}\{g_i^o=a,\ g_i^d=b,\ t_i\in r\}.$$

Trong đó, $F_{ab}^{(r)}$ biểu thị số chuyến đi từ khu vực $a$ đến khu vực $b$ trong khoảng thời gian $r$, còn $g_i^o$ và $g_i^d$ lần lượt biểu thị khu vực điểm đi và điểm đến của chuyến đi thứ $i$.

Ma trận OD đồng thời lưu giữ thông tin về vị trí và hướng của nhu cầu đi lại. Do đó, nó vừa có thể mô tả mối liên hệ giữa các khu vực, vừa có thể so sánh sự thay đổi của các mối liên hệ này theo từng khoảng thời gian.

### Điểm nóng đón và trả khách

Bằng cách cộng ma trận OD lần lượt theo chiều điểm đến và điểm đi, có thể thu được lượng chuyến xuất phát và lượng chuyến đến của từng khu vực:

$$O_a^{(r)}=\sum_bF_{ab}^{(r)},\qquad M_b^{(r)}=\sum_aF_{ab}^{(r)}.$$

Lượng chuyến xuất phát phản ánh mức độ tập trung của nhu cầu đón khách, còn lượng chuyến đến phản ánh sức hút của điểm đến. Hai đại lượng này có ý nghĩa khác nhau: một khu vực có nhiều chuyến đến không nhất thiết đồng nghĩa với việc khu vực đó đồng thời có nhu cầu đón khách cao.

Phân tích theo từng khoảng thời gian tiếp tục duy trì sự khác biệt về nhu cầu theo thời gian, qua đó cho phép bài toán lập kế hoạch lộ trình sau này cân nhắc môi trường nhu cầu tương ứng với thời điểm khởi hành.

## Trạng thái đường bộ và cơ hội nhu cầu

Lập kế hoạch lộ trình yêu cầu chuyển đổi thông tin ở cấp độ chuyến đi thành mô tả ở cấp độ đường bộ. Sau khi ánh xạ quỹ đạo lên mạng lưới đường, có thể ước lượng thời gian di chuyển, mức độ ùn tắc và cơ hội đón khách trên từng tuyến đường theo từng khoảng thời gian.

### Mức độ ùn tắc

Mức độ ùn tắc của đường có thể được mô tả bằng tỷ số giữa thời gian di chuyển lịch sử và thời gian di chuyển trong điều kiện dòng tự do:

$$q_e^{(r)}=\frac{\tau_e^{(r)}}{\tau_e^0+\varepsilon}.$$

Trong đó, $\tau_e^{(r)}$ là thời gian di chuyển lịch sử ước lượng trên đường $e$ trong khoảng thời gian $r$, $\tau_e^0$ là thời gian di chuyển trong điều kiện dòng tự do, còn $\varepsilon$ là một số dương nhỏ nhằm tránh các vấn đề về tính toán số.

Tỷ số này mô tả mức độ chậm trễ của tuyến đường so với trạng thái dòng tự do, giúp việc lựa chọn lộ trình có thể tính đến sự khác biệt về điều kiện vận hành giữa các tuyến đường và giữa các khoảng thời gian.

<img src="./images/Fig05.svg" style="width:75%" />

*Biểu diễn không gian của mức độ ùn tắc trên đường*

### Cơ hội đón khách

Cơ hội đón khách gần một tuyến đường có thể được xấp xỉ bằng tỷ lệ giữa số lần đón khách trong lịch sử và số lần tuyến đường đó được truy cập:

$$p_e^{+(r)}=\frac{N_{e,+}^{(r)}}{N_e^{(r)}+\varepsilon}.$$

Trong đó, $N_{e,+}^{(r)}$ biểu thị số lần bắt đầu đón khách gần đường $e$, còn $N_e^{(r)}$ biểu thị số lần tuyến đường đó được truy cập trong lịch sử.

Chỉ số này cung cấp thông tin về nhu cầu cho việc lựa chọn lộ trình của tài xế. Do lượng quan sát lịch sử ảnh hưởng đến độ ổn định của ước lượng, cơ hội đón khách cần được xem xét cùng với chi phí di chuyển.

<img src="./images/Fig06.svg" style="width:75%" />

*Biểu diễn không gian của cơ hội đón khách trên đường*

## Tối ưu hóa lộ trình động từ hai góc nhìn

### Góc nhìn hành khách

Từ góc nhìn của hành khách, việc lựa chọn lộ trình chủ yếu tập trung vào chi phí di chuyển để đến được điểm đích. Khoảng cách, thời gian, ùn tắc và rủi ro đường bộ cùng ảnh hưởng đến trải nghiệm chuyến đi. Vì vậy, các yếu tố khác nhau cần được chuyển đổi về những thang đo có thể so sánh trước khi kết hợp thành chi phí của từng đoạn đường.

Chi phí tổng hợp này cho phép lựa chọn lộ trình cân bằng giữa nhiều mục tiêu. Ví dụ, một đoạn đường ngắn hơn có thể có chi phí ùn tắc cao hơn, trong khi việc đi vòng ở mức hợp lý có thể cải thiện hiệu quả di chuyển tổng thể.

### Góc nhìn tài xế

Bên cạnh chi phí di chuyển, tài xế còn quan tâm đến cơ hội đón khách tiềm năng dọc theo tuyến đường. Vì vậy, đánh giá đường từ góc nhìn của tài xế cần đồng thời cân nhắc chi phí di chuyển và lợi ích tiềm năng từ nhu cầu.

Những tuyến đường có nhu cầu cao hơn có thể đáng để chấp nhận một mức chi phí di chuyển bổ sung nhất định, nhưng cơ hội nhu cầu vẫn cần bị ràng buộc bởi khoảng cách, thời gian và mức độ ùn tắc. Do đó, lựa chọn lộ trình hình thành một sự đánh đổi giữa chi phí di chuyển và lợi ích tiềm năng.

### Giải bài toán lộ trình

Biểu diễn mạng lưới đường bộ dưới dạng đồ thị, gọi $\mathcal{P}(o,d)$ là tập hợp các lộ trình khả thi từ điểm xuất phát $o$ đến điểm đích $d$, còn $C_{e,p}^{(r)}$ và $C_{e,d}^{(r)}$ lần lượt là chi phí của đường $e$ dưới góc nhìn hành khách và tài xế. Khi đó, hai bài toán lập kế hoạch lộ trình có thể được biểu diễn thống nhất như sau:

$$P_p^*=\arg\min_{P\in\mathcal{P}(o,d)}\sum_{e\in P}C_{e,p}^{(r)},$$

$$\qquad P_d^*=\arg\min_{P\in\mathcal{P}(o,d)}\sum_{e\in P}C_{e,d}^{(r)}.$$

Hai góc nhìn sử dụng cùng một mạng lưới đường bộ nhưng đánh giá giá trị của từng đoạn đường theo cách khác nhau, vì vậy có thể lựa chọn các lộ trình khác nhau. Do hàm mục tiêu của hai bài toán khác nhau, các giá trị chi phí tổng hợp không nên được so sánh trực tiếp để xác định lộ trình nào tốt hơn.

Khái niệm “động” ở đây thể hiện ở việc chi phí của đường thay đổi theo từng khoảng thời gian: cùng một đoạn đường có thể có điều kiện giao thông và cơ hội nhu cầu khác nhau ở các thời điểm khác nhau, từ đó làm thay đổi lựa chọn của toàn bộ lộ trình. Khung phương pháp này dựa trên thông tin lịch sử được phân chia theo từng khoảng thời gian.

<img src="./images/Fig07.jpg" style="width:60%" />

*Màu xanh biểu thị lộ trình từ góc nhìn hành khách, còn màu đỏ biểu thị lộ trình từ góc nhìn tài xế.*

## Tác giả và giấy phép

Để xem toàn bộ nội dung nghiên cứu, vui lòng tham khảo [*Nhận dạng mô hình di chuyển và tối ưu hóa lộ trình động dựa trên dữ liệu quỹ đạo taxi*](202602077-完整论文.pdf). Các điều kiện về sử dụng và phân phối lại dự án được quy định trong [`LICENSE`](LICENSE); các bộ dữ liệu bên ngoài và tài nguyên bản đồ cần được sử dụng theo các điều khoản cấp phép tương ứng.

**Copyright &copy; 2026 [何非凡 (HE Feifan; HÀ Phi Phàm)](https://faculty.lzjtu.edu.cn/chenmei/zh_CN/xsxx/2554/content/1835.htm)、[杜宇 (DU Yu; ĐỖ Vũ)](https://faculty.lzjtu.edu.cn/chenmei/zh_CN/xsxx/2554/content/1837.htm)、閆媛媛 (YAN Yuanyuan; DIÊM Viện Viện)。Giảng viên hướng dẫn: [ 陳梅教授 (Prof. CHEN Mei; GS. TRẦN Mai)](https://faculty.lzjtu.edu.cn/chenmei/zh_CN/index/2541/list/index.htm), Học Viện Điện Tử Và Công Nghệ Thông Tin, Đại Học Giao thông Lan Châu**
