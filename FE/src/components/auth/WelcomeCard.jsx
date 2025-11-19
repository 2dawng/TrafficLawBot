// src/components/auth/WelcomeCard.jsx
export default function WelcomeCard({ onGoogleLogin }) {
  return (
    <>
      <div className="text-center mb-8">
        <p className="text-gray-500 text-sm">
          Đăng nhập để tiếp tục sử dụng TrafficBot
        </p>
      </div>

      <button
        onClick={onGoogleLogin}
        className="cursor-pointer w-full flex items-center justify-center gap-3 py-3.5 
                   border border-gray-300 rounded-full font-semibold bg-white
                   hover:shadow-lg hover:-translate-y-1 transition-all"
      >
        <img
          src="https://www.google.com/favicon.ico"
          alt="Google"
          className="w-5 h-5"
        />
        Đăng nhập với Google
      </button>

      <p className="text-xs text-gray-500 text-center mt-6 leading-relaxed">
        Bằng việc tiếp tục, bạn đồng ý với{" "}
        <a
          href="#"
          className="font-bold hover:underline transition-all hover:text-blue-700"
        >
          Chính sách bảo mật
        </a>{" "}
        của TrafficBot.
      </p>
    </>
  );
}
