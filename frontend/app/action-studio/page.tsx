import Link from "next/link";

export default function ActionStudioPage() {
  return (
    <div className="mx-auto max-w-2xl rounded-lg border border-line bg-white p-6">
      <h1 className="text-xl font-semibold text-ink">Action Studio đã được tích hợp vào chat</h1>
      <p className="mt-2 text-sm leading-6 text-slate-600">
        Hãy hỏi Lumi trực tiếp để tạo bản nháp chuẩn bị họp, báo cáo hoặc email trả lời. Các bản nháp vẫn chỉ là nội dung để bạn kiểm tra và sử dụng thủ công.
      </p>
      <Link href="/" className="focus-ring mt-5 inline-flex h-10 items-center rounded-md bg-brand px-4 text-sm font-medium text-white hover:bg-brand-dark">
        Quay lại chat
      </Link>
    </div>
  );
}
