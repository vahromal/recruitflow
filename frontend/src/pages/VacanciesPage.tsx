import { useEffect, useState } from 'react';
import {
  Badge, Button, Card, Group, Modal, Pagination, Select, Stack, Table, Text,
  TextInput, Textarea, Title, ActionIcon, Tooltip,
} from '@mantine/core';
import { IconPlus, IconTrash } from '@tabler/icons-react';
import { useNavigate } from 'react-router-dom';
import { notifications } from '@mantine/notifications';
import { vacanciesApi } from '../api/endpoints';
import type { Page, Vacancy } from '../api/types';

const STATUS_LABEL: Record<string, string> = {
  open: 'Открыта', paused: 'На паузе', closed: 'Закрыта',
};
const STATUS_COLOR: Record<string, string> = {
  open: 'green', paused: 'orange', closed: 'gray',
};

const emptyForm = {
  title: '', client: '', description: '', requirements: '',
  salary_min: '', salary_max: '', status: 'open',
};

export default function VacanciesPage() {
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const [data, setData] = useState<Page<Vacancy> | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [opened, setOpened] = useState(false);
  const [form, setForm] = useState({ ...emptyForm });
  const [busy, setBusy] = useState(false);

  const load = () => {
    vacanciesApi
      .list({ page, page_size: 20, status: status ?? undefined })
      .then(setData)
      .catch((e) => notifications.show({ color: 'red', message: e.message }));
  };

  useEffect(load, [page, status]);

  const create = async () => {
    setBusy(true);
    try {
      const v = await vacanciesApi.create({
        title: form.title,
        client: form.client || null,
        description: form.description || null,
        requirements: form.requirements || null,
        salary_min: form.salary_min ? Number(form.salary_min) : null,
        salary_max: form.salary_max ? Number(form.salary_max) : null,
        status: form.status,
      } as Partial<Vacancy>);
      notifications.show({ color: 'green', message: 'Вакансия создана' });
      setOpened(false);
      setForm({ ...emptyForm });
      navigate(`/vacancies/${v.id}/board`);
    } catch (e) {
      notifications.show({ color: 'red', message: e instanceof Error ? e.message : 'Ошибка' });
    } finally {
      setBusy(false);
    }
  };

  const changeStatus = (v: Vacancy, next: string) =>
    vacanciesApi
      .update(v.id, { status: next as Vacancy['status'] })
      .then(() => {
        notifications.show({ color: 'green', message: `Статус: ${STATUS_LABEL[next]}` });
        load();
      })
      .catch((e) => notifications.show({ color: 'red', message: e.message }));

  const remove = async (v: Vacancy) => {
    if (!window.confirm(`Удалить вакансию «${v.title}» вместе с карточками кандидатов?`)) return;
    try {
      await vacanciesApi.remove(v.id);
      load();
    } catch (e) {
      notifications.show({ color: 'red', message: e instanceof Error ? e.message : 'Ошибка' });
    }
  };

  return (
    <Stack>
      <Group justify="space-between">
        <Title order={2}>Вакансии</Title>
        <Button leftSection={<IconPlus size={16} />} onClick={() => setOpened(true)}>
          Создать
        </Button>
      </Group>

      <Group>
        <Select
          placeholder="Все статусы" clearable w={180}
          data={Object.entries(STATUS_LABEL).map(([value, label]) => ({ value, label }))}
          value={status}
          onChange={(v) => { setPage(1); setStatus(v); }}
        />
      </Group>

      <Card withBorder padding="sm">
        <Table>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Название</Table.Th>
              <Table.Th>Клиент</Table.Th>
              <Table.Th>Вилка</Table.Th>
              <Table.Th>Статус</Table.Th>
              <Table.Th>Обновлено</Table.Th>
              <Table.Th />
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {data?.items.map((v) => (
              <Table.Tr key={v.id}>
                <Table.Td
                  fw={500}
                  style={{ cursor: 'pointer' }}
                  onClick={() => navigate(`/vacancies/${v.id}/board`)}
                >
                  {v.title}
                </Table.Td>
                <Table.Td>{v.client ?? '—'}</Table.Td>
                <Table.Td>
                  {v.salary_min && v.salary_max
                    ? `${v.salary_min.toLocaleString('ru-RU')} – ${v.salary_max.toLocaleString('ru-RU')}`
                    : '—'}
                </Table.Td>
                <Table.Td>
                  <Select
                    size="xs"
                    w={130}
                    data={Object.entries(STATUS_LABEL).map(([value, label]) => ({ value, label }))}
                    value={v.status}
                    onChange={(next) => next && changeStatus(v, next)}
                  />
                </Table.Td>
                <Table.Td>{new Date(v.updated_at).toLocaleDateString('ru-RU')}</Table.Td>
                <Table.Td>
                  <Group gap={4} justify="flex-end">
                    <Button
                      size="compact-xs" variant="light"
                      onClick={() => navigate(`/vacancies/${v.id}/board`)}
                    >
                      Канбан
                    </Button>
                    <Tooltip label="Удалить">
                      <ActionIcon color="red" variant="subtle" onClick={() => remove(v)}>
                        <IconTrash size={16} />
                      </ActionIcon>
                    </Tooltip>
                  </Group>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
        {data && data.total === 0 && (
          <Text c="dimmed" size="sm" ta="center" py="md">Вакансий нет</Text>
        )}
      </Card>

      {data && data.total > 20 && (
        <Pagination value={page} onChange={setPage} total={Math.ceil(data.total / 20)} />
      )}

      <Modal opened={opened} onClose={() => setOpened(false)} title="Новая вакансия" size="lg">
        <Stack>
          <TextInput label="Название *" required value={form.title}
            onChange={(e) => setForm({ ...form, title: e.currentTarget.value })} />
          <TextInput label="Клиент" value={form.client}
            onChange={(e) => setForm({ ...form, client: e.currentTarget.value })} />
          <Textarea label="Описание" rows={3} value={form.description}
            onChange={(e) => setForm({ ...form, description: e.currentTarget.value })} />
          <Textarea label="Требования" rows={3} value={form.requirements}
            onChange={(e) => setForm({ ...form, requirements: e.currentTarget.value })} />
          <Group grow>
            <TextInput label="Зарплата от" value={form.salary_min}
              onChange={(e) => setForm({ ...form, salary_min: e.currentTarget.value })} />
            <TextInput label="Зарплата до" value={form.salary_max}
              onChange={(e) => setForm({ ...form, salary_max: e.currentTarget.value })} />
          </Group>
          <Select label="Статус" data={Object.entries(STATUS_LABEL).map(([value, label]) => ({ value, label }))}
            value={form.status} onChange={(v) => setForm({ ...form, status: v ?? 'open' })} />
          <Button onClick={create} loading={busy} disabled={!form.title.trim()}>Создать</Button>
        </Stack>
      </Modal>
    </Stack>
  );
}
