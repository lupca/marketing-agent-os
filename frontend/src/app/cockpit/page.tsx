import CockpitLayout from '@/components/cockpit/CockpitLayout';
import AuthGuard from '@/components/AuthGuard';

export const metadata = {
  title: 'The Autopilot Cockpit | Marketing Agent OS',
  description: 'Human-ON-the-loop observability and debugging for the autonomous AI engine',
};

export default function CockpitPage() {
  return (
    <AuthGuard>
      <CockpitLayout />
    </AuthGuard>
  );
}

