// src/components/auth/LoginCard.jsx
import { useState } from 'react';
import { ArrowLeft } from 'lucide-react';

export default function LoginCard({ onBack, isRegister = false, onSwitchToRegister }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  return (
    <>
      <button
        onClick={onBack}
        className="mb-6 text-blue-600 hover:underline flex items-center gap-1 text-sm font-medium cursor-pointer"
      >
        <ArrowLeft className="w-4 h-4" />
        Quay lại
      </button>

      <h2 className="text-2xl font-bold text-center mb-6">
        {isRegister ? 'Tạo tài khoản mới' : 'Chào mừng trở lại!'}
      </h2>

      <form className="space-y-5">
        <input
          type="email"
          placeholder="Email của bạn"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="w-full px-4 py-3 border border-gray-300 rounded-full focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
        />
        <input
          type="password"
          placeholder="Mật khẩu"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="w-full px-4 py-3 border border-gray-300 rounded-full focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
        />
        {isRegister && (
          <input
            type="password"
            placeholder="Nhập lại mật khẩu"
            className="w-full px-4 py-3 border border-gray-300 rounded-full focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
          />
        )}

        <button
          type="submit"
          className="w-full py-3.5 bg-gradient-to-r from-blue-600 to-purple-600 text-white font-bold rounded-full hover:shadow-xl transform cursor-pointer transition-all"
        >
          {isRegister ? 'ĐĂNG KÝ NGAY' : 'ĐĂNG NHẬP'}
        </button>
        <p className="text-center mt-5 text-sm text-gray-600">
        Chưa có tài khoản?{' '}
        <button
          onClick={onSwitchToRegister}
          className="text-blue-600 font-semibold hover:underline cursor-pointer"
        >
          Đăng ký ngay
        </button>
      </p>
      </form>

      {!isRegister && (
        <p className="text-center mt-4 text-sm">
          <a href="#" className="text-blue-600 hover:underline">Quên mật khẩu?</a>
        </p>
      )}
    </>
  );
}