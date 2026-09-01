import React, { useState } from 'react';
import { Modal } from '../common/Modal';
import { Button } from '../common/Button';
import { ShieldCheck, Mail, Lock, KeyRound, Building2 } from 'lucide-react';
import { DEMO_INSPECTOR } from '../../services/authService';

export interface LoginModalProps {
  isOpen: boolean;
  onClose: () => void;
  onLogin: (credentials: { email: string; password?: string; badgeId?: string }) => Promise<boolean>;
  isLoading?: boolean;
}

export const LoginModal: React.FC<LoginModalProps> = ({
  isOpen,
  onClose,
  onLogin,
  isLoading = false,
}) => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [badgeId, setBadgeId] = useState('');
  const [isForgotPass, setIsForgotPass] = useState(false);
  const [forgotSent, setForgotSent] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email) return;
    const success = await onLogin({ email, password, badgeId });
    if (success) {
      onClose();
    }
  };

  const handleDemoLogin = async () => {
    const success = await onLogin({
      email: DEMO_INSPECTOR.email,
      badgeId: DEMO_INSPECTOR.badgeId,
    });
    if (success) {
      onClose();
    }
  };

  const handleForgotSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setForgotSent(true);
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      maxWidth="md"
      title={isForgotPass ? 'Reset Inspector Credentials' : 'Legal Metrology Portal Sign-In'}
      subtitle={
        isForgotPass
          ? 'Enter your official government email to receive password reset instructions.'
          : 'Access packaged commodity inspection records and compliance reports.'
      }
    >
      {isForgotPass ? (
        forgotSent ? (
          <div className="text-center py-4">
            <div className="w-12 h-12 rounded-full bg-emerald-50 text-emerald-600 flex items-center justify-center mx-auto mb-3">
              <ShieldCheck className="w-6 h-6" />
            </div>
            <h4 className="text-sm font-semibold text-slate-800 mb-1">Reset Instructions Dispatched</h4>
            <p className="text-xs text-slate-500 mb-6">
              If an account matches <span className="font-medium text-slate-700">{email}</span>, a secure authentication link has been sent.
            </p>
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                setIsForgotPass(false);
                setForgotSent(false);
              }}
              className="w-full"
            >
              Back to Sign In
            </Button>
          </div>
        ) : (
          <form onSubmit={handleForgotSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-slate-700 mb-1.5">Official Email</label>
              <div className="relative">
                <Mail className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="email"
                  required
                  placeholder="officer@metrology.gov.in"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full pl-9 pr-3.5 py-2 text-sm bg-slate-50 border border-slate-200 rounded-lg focus:bg-white focus:outline-none focus:ring-2 focus:ring-primary-800"
                />
              </div>
            </div>
            <div className="flex gap-2 pt-2">
              <Button
                variant="outline"
                size="md"
                onClick={() => setIsForgotPass(false)}
                className="w-1/2"
              >
                Cancel
              </Button>
              <Button type="submit" variant="primary" size="md" className="w-1/2">
                Send Link
              </Button>
            </div>
          </form>
        )
      ) : (
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1.5">
              Government / Inspector Email
            </label>
            <div className="relative">
              <Mail className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="email"
                required
                placeholder="rajesh.kumar@metrology.gov.in"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full pl-9 pr-3.5 py-2 text-sm bg-slate-50 border border-slate-200 rounded-lg focus:bg-white focus:outline-none focus:ring-2 focus:ring-primary-800"
              />
            </div>
          </div>

          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="block text-xs font-medium text-slate-700">Password</label>
              <button
                type="button"
                onClick={() => setIsForgotPass(true)}
                className="text-xs text-primary-700 hover:text-primary-800 hover:underline"
              >
                Forgot password?
              </button>
            </div>
            <div className="relative">
              <Lock className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full pl-9 pr-3.5 py-2 text-sm bg-slate-50 border border-slate-200 rounded-lg focus:bg-white focus:outline-none focus:ring-2 focus:ring-primary-800"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1.5">
              Officer Badge / Station ID (Optional)
            </label>
            <div className="relative">
              <Building2 className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="e.g. LM-DEL-8814"
                value={badgeId}
                onChange={(e) => setBadgeId(e.target.value)}
                className="w-full pl-9 pr-3.5 py-2 text-sm bg-slate-50 border border-slate-200 rounded-lg focus:bg-white focus:outline-none focus:ring-2 focus:ring-primary-800 font-mono text-xs uppercase"
              />
            </div>
          </div>

          <div className="pt-2 flex flex-col gap-2">
            <Button
              type="submit"
              variant="primary"
              size="md"
              isLoading={isLoading}
              className="w-full"
            >
              Sign In to Terminal
            </Button>

            <div className="relative my-2">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-slate-200" />
              </div>
              <div className="relative flex justify-center text-xs uppercase">
                <span className="bg-white px-2 text-slate-400">or quick access for demo</span>
              </div>
            </div>

            <Button
              type="button"
              variant="secondary"
              size="md"
              onClick={handleDemoLogin}
              leftIcon={<KeyRound className="w-4 h-4 text-primary-700" />}
              className="w-full text-xs font-medium text-slate-700 border border-slate-200/80"
            >
              Demo: Sign In as Inspector Rajesh Kumar
            </Button>
          </div>

          <div className="text-center pt-2">
            <p className="text-xs text-slate-500">
              Need departmental registration?{' '}
              <a
                href="#register"
                onClick={(e) => {
                  e.preventDefault();
                  alert('Officer registrations are provisioned through State Legal Metrology Headquarters.');
                }}
                className="text-primary-800 font-medium hover:underline"
              >
                Request Officer Credentials
              </a>
            </p>
          </div>
        </form>
      )}
    </Modal>
  );
};
