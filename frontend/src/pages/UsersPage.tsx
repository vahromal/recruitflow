import { useEffect, useState } from 'react';
import {
  Button, Card, Group, Modal, PasswordInput, Switch, Table, Text, TextInput,
  Title, Select,
} from '@mantine/core';
import { IconPlus } from '@tabler/icons-react';
import { notifications } from '@mantine/notifications';
import { usersApi } from '../api/endpoints';
import type { User } from '../api/types';
import { useAuth } from '../hooks/useAuth';

const emptyForm = { email: '', full_name: '', password: '', role: 'recruiter' };

export default function UsersPage() {
  const { user: me } = useAuth();
  const [users, setUsers] = useState<User[]>([]);
  const [opened, setOpened] = useState(false);
  const [form, setForm] = useState({ ...emptyForm });
  const [busy, setBusy] = useState(false);

  const load = () =>
    usersApi
      .list()
      .then(setUsers)
      .catch((e) => notifications.show({ color: 'red', message: e.message }));

  useEffect(() => {
    load();
  }, []);

  const create = async () => {
    setBusy(true);
    try {
      await usersApi.create(form);
      notifications.show({ color: 'green', message: 'Пользователь создан' });
      setOpened(false);
      setForm({ ...emptyForm });
      load();
    } catch (e) {
      notifications.show({ color: 'red', message: e instanceof Error ? e.message : 'Ошибка' });
    } finally {
      setBusy(false);
    }
  };

  const toggleActive = (u: User) =>
    usersApi
      .update(u.id, { is_active: !u.is_active })
      .then(load)
      .catch((e) => notifications.show({ color: 'red', message: e.message }));

  const changeRole = (u: User, role: string) =>
    usersApi
      .update(u.id, { role })
      .then(() => {
        notifications.show({ color: 'green', message: 'Роль обновлена' });
        load();
      })
      .catch((e) => notifications.show({ color: 'red', message: e.message }));

  const remove = async (u: User) => {
    if (!window.confirm(`Удалить пользователя ${u.email}?`)) return;
    try {
      await usersApi.remove(u.id);
      load();
    } catch (e) {
      notifications.show({ color: 'red', message: e instanceof Error ? e.message : 'Ошибка' });
    }
  };

  return (
    <div>
      <Group justify="space-between" mb="md">
        <Title order={2}>Пользователи</Title>
        <Button leftSection={<IconPlus size={16} />} onClick={() => setOpened(true)}>
          Добавить
        </Button>
      </Group>

      <Card withBorder padding="sm">
        <Table>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Имя</Table.Th>
              <Table.Th>Email</Table.Th>
              <Table.Th>Роль</Table.Th>
              <Table.Th>Активен</Table.Th>
              <Table.Th />
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {users.map((u) => (
              <Table.Tr key={u.id}>
                <Table.Td>{u.full_name}</Table.Td>
                <Table.Td>{u.email}</Table.Td>
                <Table.Td>
                  <Select
                    size="xs" w={150}
                    data={[
                      { value: 'admin', label: 'Администратор' },
                      { value: 'recruiter', label: 'Рекрутер' },
                    ]}
                    value={u.role}
                    disabled={u.id === me?.id}
                    onChange={(v) => v && changeRole(u, v)}
                  />
                </Table.Td>
                <Table.Td>
                  <Switch
                    checked={u.is_active}
                    disabled={u.id === me?.id}
                    onChange={() => toggleActive(u)}
                    label={u.is_active ? 'Да' : 'Нет'}
                    labelPosition="left"
                  />
                </Table.Td>
                <Table.Td ta="right">
                  <Button
                    size="compact-xs" color="red" variant="subtle"
                    disabled={u.id === me?.id}
                    onClick={() => remove(u)}
                  >
                    Удалить
                  </Button>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
        {users.length === 0 && (
          <Text c="dimmed" size="sm" ta="center" py="md">Пользователей нет</Text>
        )}
      </Card>

      <Modal opened={opened} onClose={() => setOpened(false)} title="Новый пользователь">
        <div>
          <TextInput label="Имя *" required mb="sm" value={form.full_name}
            onChange={(e) => setForm({ ...form, full_name: e.currentTarget.value })} />
          <TextInput label="Email *" required type="email" mb="sm" value={form.email}
            onChange={(e) => setForm({ ...form, email: e.currentTarget.value })} />
          <PasswordInput label="Пароль * (мин. 8 символов)" required mb="sm" value={form.password}
            onChange={(e) => setForm({ ...form, password: e.currentTarget.value })} />
          <Select label="Роль" data={[
            { value: 'recruiter', label: 'Рекрутер' },
            { value: 'admin', label: 'Администратор' },
          ]} value={form.role} onChange={(v) => setForm({ ...form, role: v ?? 'recruiter' })}
            mb="lg" />
          <Button onClick={create} loading={busy}
            disabled={!form.email || !form.full_name || form.password.length < 8}>
            Создать
          </Button>
        </div>
      </Modal>
    </div>
  );
}
