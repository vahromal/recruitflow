import { useEffect, useState } from 'react';
import {
  Button, Card, FileInput, Group, Modal, Pagination, Stack, Table, Text,
  TextInput, Title, Select, ActionIcon, Tooltip,
} from '@mantine/core';
import { IconDownload, IconPlus, IconUpload, IconTrash } from '@tabler/icons-react';
import { useNavigate } from 'react-router-dom';
import { notifications } from '@mantine/notifications';
import { candidatesApi } from '../api/endpoints';
import type { Candidate, Page } from '../api/types';
import { useAuth } from '../hooks/useAuth';

const emptyForm = {
  full_name: '', phone: '', email: '', city: '', position: '', company: '',
  expected_salary: '', source: '', telegram: '', whatsapp: '', notes: '', tags: '',
};

export default function CandidatesPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const [data, setData] = useState<Page<Candidate> | null>(null);
  const [q, setQ] = useState('');
  const [city, setCity] = useState('');
  const [tag, setTag] = useState('');
  const [opened, setOpened] = useState(false);
  const [form, setForm] = useState({ ...emptyForm });
  const [resume, setResume] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);

  const load = () => {
    candidatesApi
      .list({ page, page_size: 20, q: q || undefined, city: city || undefined, tag: tag || undefined })
      .then(setData)
      .catch((e) => notifications.show({ color: 'red', message: e.message }));
  };

  useEffect(load, [page, q, city, tag]);

  const create = async () => {
    setBusy(true);
    try {
      const tags = form.tags.split(',').map((t) => t.trim()).filter(Boolean);
      const candidate = await candidatesApi.create({
        full_name: form.full_name,
        phone: form.phone || null,
        email: form.email || null,
        city: form.city || null,
        position: form.position || null,
        company: form.company || null,
        expected_salary: form.expected_salary ? Number(form.expected_salary) : null,
        source: form.source || null,
        telegram: form.telegram || null,
        whatsapp: form.whatsapp || null,
        notes: form.notes || null,
        tags,
      } as Partial<Candidate>);
      if (resume) await candidatesApi.uploadResume(candidate.id, resume);
      notifications.show({ color: 'green', message: 'Кандидат создан' });
      setOpened(false);
      setForm({ ...emptyForm });
      setResume(null);
      load();
    } catch (e) {
      notifications.show({
        color: 'red',
        message: e instanceof Error ? e.message : 'Ошибка создания',
      });
    } finally {
      setBusy(false);
    }
  };

  const remove = async (c: Candidate) => {
    // no confirmation UI lib usage: keep native confirm for simplicity
    if (!window.confirm(`Удалить кандидата «${c.full_name}»? Это нельзя отменить.`)) return;
    try {
      await candidatesApi.remove(c.id);
      notifications.show({ color: 'green', message: 'Кандидат удалён' });
      load();
    } catch (e) {
      notifications.show({ color: 'red', message: e instanceof Error ? e.message : 'Ошибка' });
    }
  };

  return (
    <Stack>
      <Group justify="space-between">
        <Title order={2}>Кандидаты</Title>
        <Group>
          <Button
            variant="light"
            leftSection={<IconDownload size={16} />}
            onClick={() => candidatesApi.exportCsv(q || undefined).catch((e) =>
              notifications.show({ color: 'red', message: e.message }))}
          >
            CSV
          </Button>
          <Button leftSection={<IconPlus size={16} />} onClick={() => setOpened(true)}>
            Добавить
          </Button>
        </Group>
      </Group>

      <Group>
        <TextInput
          placeholder="Поиск: имя, email, телефон, компания…"
          value={q}
          onChange={(e) => { setPage(1); setQ(e.currentTarget.value); }}
          w={320}
        />
        <TextInput
          placeholder="Город"
          value={city}
          onChange={(e) => { setPage(1); setCity(e.currentTarget.value); }}
          w={160}
        />
        <TextInput
          placeholder="Тег"
          value={tag}
          onChange={(e) => { setPage(1); setTag(e.currentTarget.value); }}
          w={120}
        />
      </Group>

      <Card withBorder padding="sm">
        <Table>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>ФИО</Table.Th>
              <Table.Th>Контакты</Table.Th>
              <Table.Th>Должность</Table.Th>
              <Table.Th>Город</Table.Th>
              <Table.Th ta="right">Зарплата</Table.Th>
              <Table.Th>Теги</Table.Th>
              <Table.Th />
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {data?.items.map((c) => (
              <Table.Tr
                key={c.id}
                style={{ cursor: 'pointer' }}
                onClick={() => navigate(`/candidates/${c.id}`)}
              >
                <Table.Td fw={500}>{c.full_name}</Table.Td>
                <Table.Td>
                  <Text size="sm">{c.email}</Text>
                  <Text size="xs" c="dimmed">{c.phone}</Text>
                </Table.Td>
                <Table.Td>{c.position}</Table.Td>
                <Table.Td>{c.city}</Table.Td>
                <Table.Td ta="right">
                  {c.expected_salary ? c.expected_salary.toLocaleString('ru-RU') : '—'}
                </Table.Td>
                <Table.Td>
                  {c.tags?.map((t) => (
                    <Text key={t} span size="xs" mr={4} c="blue">{`#${t}`}</Text>
                  ))}
                </Table.Td>
                <Table.Td onClick={(e) => e.stopPropagation()}>
                  <Tooltip label="Удалить">
                    <ActionIcon color="red" variant="subtle" onClick={() => remove(c)}>
                      <IconTrash size={16} />
                    </ActionIcon>
                  </Tooltip>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
        {data && data.total === 0 && (
          <Text c="dimmed" size="sm" ta="center" py="md">Ничего не найдено</Text>
        )}
      </Card>

      {data && data.total > 20 && (
        <Pagination value={page} onChange={setPage} total={Math.ceil(data.total / 20)} />
      )}

      <Modal opened={opened} onClose={() => setOpened(false)} title="Новый кандидат" size="lg">
        <Stack>
          <TextInput label="ФИО *" required value={form.full_name}
            onChange={(e) => setForm({ ...form, full_name: e.currentTarget.value })} />
          <Group grow>
            <TextInput label="Телефон" value={form.phone}
              onChange={(e) => setForm({ ...form, phone: e.currentTarget.value })} />
            <TextInput label="Email" value={form.email}
              onChange={(e) => setForm({ ...form, email: e.currentTarget.value })} />
          </Group>
          <Group grow>
            <TextInput label="Город" value={form.city}
              onChange={(e) => setForm({ ...form, city: e.currentTarget.value })} />
            <TextInput label="Должность" value={form.position}
              onChange={(e) => setForm({ ...form, position: e.currentTarget.value })} />
          </Group>
          <Group grow>
            <TextInput label="Компания" value={form.company}
              onChange={(e) => setForm({ ...form, company: e.currentTarget.value })} />
            <TextInput label="Ожидаемая зарплата" value={form.expected_salary}
              onChange={(e) => setForm({ ...form, expected_salary: e.currentTarget.value })} />
          </Group>
          <Group grow>
            <TextInput label="Telegram" value={form.telegram}
              onChange={(e) => setForm({ ...form, telegram: e.currentTarget.value })} />
            <TextInput label="WhatsApp" value={form.whatsapp}
              onChange={(e) => setForm({ ...form, whatsapp: e.currentTarget.value })} />
          </Group>
          <Group grow>
            <TextInput label="Источник" value={form.source}
              onChange={(e) => setForm({ ...form, source: e.currentTarget.value })} />
            <TextInput label="Теги (через запятую)" value={form.tags}
              onChange={(e) => setForm({ ...form, tags: e.currentTarget.value })} />
          </Group>
          <TextInput label="Заметки" value={form.notes}
            onChange={(e) => setForm({ ...form, notes: e.currentTarget.value })} />
          <FileInput
            label="Резюме (PDF/DOCX)"
            placeholder={resume?.name ?? 'Выберите файл'}
            accept=".pdf,.docx"
            value={resume}
            onChange={setResume}
            leftSection={<IconUpload size={16} />}
          />
          <Button onClick={create} loading={busy} disabled={!form.full_name.trim()}>
            Создать
          </Button>
        </Stack>
      </Modal>
    </Stack>
  );
}
