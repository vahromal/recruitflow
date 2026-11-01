import { NavLink, Stack, Text, UnstyledButton } from '@mantine/core';
import {
  IconBuilding, IconLayoutDashboard, IconLogout, IconUsers, IconUserCircle,
} from '@tabler/icons-react';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';

const links = [
  { to: '/', label: 'Дашборд', icon: IconLayoutDashboard },
  { to: '/candidates', label: 'Кандидаты', icon: IconUserCircle },
  { to: '/vacancies', label: 'Вакансии', icon: IconBuilding },
];

export default function AppLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>
      <aside
        style={{
          width: 230, padding: 16, borderRight: '1px solid #e9ecef',
          display: 'flex', flexDirection: 'column',
        }}
      >
        <Text fw={700} size="lg" mb="md">
          RecruitFlow
        </Text>
        <Stack gap={4}>
          {links.map(({ to, label, icon: Icon }) => (
            <UnstyledButton
              key={to}
              onClick={() => navigate(to)}
              style={{
                padding: '8px 10px',
                borderRadius: 6,
                background: location.pathname === to ? '#e7f5ff' : 'transparent',
                color: location.pathname === to ? '#1971c2' : '#495057',
                display: 'flex', alignItems: 'center', gap: 8,
                cursor: 'pointer',
              }}
            >
              <Icon size={18} />
              <span>{label}</span>
            </UnstyledButton>
          ))}
          {user?.role === 'admin' && (
            <UnstyledButton
              onClick={() => navigate('/users')}
              style={{
                padding: '8px 10px', borderRadius: 6,
                background: location.pathname === '/users' ? '#e7f5ff' : 'transparent',
                color: location.pathname === '/users' ? '#1971c2' : '#495057',
                display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer',
              }}
            >
              <IconUsers size={18} />
              <span>Пользователи</span>
            </UnstyledButton>
          )}
        </Stack>

        <div style={{ marginTop: 'auto' }}>
          <Text size="sm" c="dimmed">
            {user?.full_name}
          </Text>
          <Text size="xs" c="dimmed">
            {user?.role === 'admin' ? 'Администратор' : 'Рекрутер'}
          </Text>
          <NavLink
            label="Выйти"
            leftSection={<IconLogout size={16} />}
            onClick={() => {
              logout();
              navigate('/login');
            }}
            mt="sm"
          />
        </div>
      </aside>

      <main style={{ flex: 1, padding: 24, minWidth: 0 }}>
        <Outlet />
      </main>
    </div>
  );
}
