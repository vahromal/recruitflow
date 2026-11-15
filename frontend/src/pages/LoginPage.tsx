import { useState } from 'react';
import {
  Alert, Button, Card, Center, PasswordInput, Stack, Text, TextInput, Title,
} from '@mantine/core';
import { IconAlertCircle } from '@tabler/icons-react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { healthUrl } from '../api/base';

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await login(email, password);
      navigate('/');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ошибка входа');
    } finally {
      setBusy(false);
    }
  };

  return (
    <Center h="100vh">
      <Card w={380} withBorder padding="xl">
        <Title order={2} mb="xs">
          RecruitFlow
        </Title>
        <Text c="dimmed" size="sm" mb="lg">
          Вход в CRM для рекрутеров
        </Text>
        <form onSubmit={submit}>
          <Stack>
            {error && (
              <Alert icon={<IconAlertCircle size={16} />} color="red">
                {error}
                <Text size="xs" mt={6} c="dimmed">
                  Проверить доступность API:{' '}
                  <a href={healthUrl()} target="_blank" rel="noreferrer">
                    {healthUrl()}
                  </a>
                </Text>
              </Alert>
            )}
            <TextInput
              label="Email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.currentTarget.value)}
              autoComplete="username"
            />
            <PasswordInput
              label="Пароль"
              required
              value={password}
              onChange={(e) => setPassword(e.currentTarget.value)}
              autoComplete="current-password"
            />
            <Button type="submit" loading={busy}>
              Войти
            </Button>
          </Stack>
        </form>
      </Card>
    </Center>
  );
}
