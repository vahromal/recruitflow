import { useCallback, useEffect, useState } from 'react';
import {
  Badge, Button, Card, Checkbox, Group, Loader, Stack, Table, Text, Textarea,
  TextInput, Title, FileInput, Select, Divider,
} from '@mantine/core';
import { IconDownload, IconFileUpload, IconTrash, IconLock } from '@tabler/icons-react';
import { useNavigate, useParams } from 'react-router-dom';
import { notifications } from '@mantine/notifications';
import { activitiesApi, candidatesApi, gdprApi, vacanciesApi } from '../api/endpoints';
import type { Activity, Candidate, Vacancy } from '../api/types';
import { STAGES } from '../api/types';

export default function CandidateDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const cid = Number(id);
  const [candidate, setCandidate] = useState<Awaited<ReturnType<typeof candidatesApi.get>> | null>(null);
  const [activities, setActivities] = useState<Activity[]>([]);
  const [vacancies, setVacancies] = useState<Vacancy[]>([]);
  const [comment, setComment] = useState('');
  const [taskBody, setTaskBody] = useState('');
  const [taskDue, setTaskDue] = useState<string>('');
  const [addingToVacancy, setAddingToVacancy] = useState<string | null>('');
  const [resume, setResume] = useState<File | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(() => {
    candidatesApi
      .get(cid)
      .then((d) => setCandidate(d))
      .catch((e) => notifications.show({ color: 'red', message: e.message }))
      .finally(() => setLoading(false));
    activitiesApi.list(cid).then(setActivities).catch(() => {});
    vacanciesApi.list({ page_size: 100 }).then((p) => setVacancies(p.items)).catch(() => {});
  }, [cid]);

  useEffect(load, [load]);

  if (loading) return <Loader />;
  if (!candidate) return <Text c="red">Кандидат не найден</Text>;

  const run = (fn: () => Promise<unknown>, msg: string, reload = true) =>
    fn()
      .then(() => {
        notifications.show({ color: 'green', message: msg });
        if (reload) load();
      })
      .catch((e) => notifications.show({ color: 'red', message: e.message ?? 'Ошибка' }));

  const uploadResume = () => {
    if (!resume) return;
    run(() => candidatesApi.uploadResume(cid, resume), 'Резюме загружено');
    setResume(null);
  };

  const completeTask = (t: Activity) =>
    run(() => activitiesApi.updateTask(t.id, { task_status: 'done' }), 'Задача выполнена');

  return (
    <Stack>
      <Group justify="space-between">
        <div>
          <Title order={2}>{candidate.full_name}</Title>
          <Text c="dimmed" size="sm">
            {[candidate.position, candidate.company, candidate.city].filter(Boolean).join(' · ')}
          </Text>
        </div>
        <Group>
          <Button
            variant="light"
            leftSection={<IconDownload size={16} />}
            onClick={() => run(() => gdprApi.exportCandidate(cid), 'Экспорт GDPR скачан', false)}
          >
            Экспорт данных
          </Button>
          <Button
            color="red"
            variant="light"
            leftSection={<IconLock size={16} />}
            onClick={() => {
              if (window.confirm('Удалить все персональные данные кандидата (GDPR)?')) {
                run(() => gdprApi.eraseCandidate(cid), 'Данные удалены', false).then(() =>
                  navigate('/candidates'));
              }
            }}
          >
            Удалить данные
          </Button>
        </Group>
      </Group>

      <Card withBorder>
        <Title order={5} mb="sm">Контакты и профиль</Title>
        <Table>
          <Table.Tbody>
            <Table.Tr>
              <Table.Td w={220} c="dimmed">Email</Table.Td><Table.Td>{candidate.email ?? '—'}</Table.Td>
              <Table.Td w={220} c="dimmed">Телефон</Table.Td><Table.Td>{candidate.phone ?? '—'}</Table.Td>
            </Table.Tr>
            <Table.Tr>
              <Table.Td c="dimmed">Telegram</Table.Td><Table.Td>{candidate.telegram ?? '—'}</Table.Td>
              <Table.Td c="dimmed">WhatsApp</Table.Td><Table.Td>{candidate.whatsapp ?? '—'}</Table.Td>
            </Table.Tr>
            <Table.Tr>
              <Table.Td c="dimmed">Ожидаемая зарплата</Table.Td>
              <Table.Td>{candidate.expected_salary ? candidate.expected_salary.toLocaleString('ru-RU') : '—'}</Table.Td>
              <Table.Td c="dimmed">Источник</Table.Td><Table.Td>{candidate.source ?? '—'}</Table.Td>
            </Table.Tr>
            <Table.Tr>
              <Table.Td c="dimmed">Теги</Table.Td>
              <Table.Td>{candidate.tags?.length ? candidate.tags.map((t) => `#${t}`).join(' ') : '—'}</Table.Td>
              <Table.Td c="dimmed">Заметки</Table.Td><Table.Td>{candidate.notes ?? '—'}</Table.Td>
            </Table.Tr>
          </Table.Tbody>
        </Table>
      </Card>

      <Card withBorder>
        <Title order={5} mb="sm">Резюме</Title>
        <Group>
          {candidate.resume_filename ? (
            <>
              <Text size="sm">{candidate.resume_filename}</Text>
              <Button
                size="xs" variant="light"
                leftSection={<IconDownload size={14} />}
                onClick={async () => {
                  const res = await fetch(`/api/candidates/${cid}/resume`, {
                    headers: { Authorization: `Bearer ${localStorage.getItem('rf_token') ?? ''}` },
                  });
                  const blob = await res.blob();
                  const url = URL.createObjectURL(blob);
                  const a = document.createElement('a');
                  a.href = url;
                  a.download = candidate.resume_filename ?? 'resume';
                  a.click();
                  URL.revokeObjectURL(url);
                }}
              >
                Скачать
              </Button>
            </>
          ) : (
            <Text c="dimmed" size="sm">Файл не загружен</Text>
          )}
        </Group>
        <Group mt="sm">
          <FileInput
            accept=".pdf,.docx" value={resume} onChange={setResume}
            placeholder="PDF или DOCX" style={{ minWidth: 240 }}
            leftSection={<IconFileUpload size={16} />}
          />
          <Button size="sm" onClick={uploadResume} disabled={!resume}>Загрузить</Button>
        </Group>
      </Card>

      <Card withBorder>
        <Title order={5} mb="sm">Воронка (вакансии)</Title>
        {candidate.stages?.length ? (
          <Table>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Вакансия</Table.Th>
                <Table.Th>Стадия</Table.Th>
                <Table.Th>Причина отказа</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {candidate.stages.map((st: { id: number; vacancy_id: number; stage: string; reject_reason: string | null }) => (
                <Table.Tr key={st.id}>
                  <Table.Td>
                    <a href={`/vacancies/${st.vacancy_id}/board`}>
                      {vacancies.find((v) => v.id === st.vacancy_id)?.title ?? `#${st.vacancy_id}`}
                    </a>
                  </Table.Td>
                  <Table.Td>
                    <Badge color={st.stage === 'hired' ? 'green' : st.stage === 'rejected' ? 'red' : 'blue'}>
                      {STAGES.find((s) => s.value === st.stage)?.label ?? st.stage}
                    </Badge>
                  </Table.Td>
                  <Table.Td>{st.reject_reason ?? '—'}</Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        ) : (
          <Group align="flex-end">
            <Select
              label="Добавить на вакансию"
              placeholder="Выберите вакансию"
              data={vacancies.map((v) => ({ value: String(v.id), label: `${v.title} — ${v.client ?? ''}` }))}
              value={addingToVacancy}
              onChange={setAddingToVacancy}
              w={360}
            />
            <Button
              size="sm"
              disabled={!addingToVacancy}
              onClick={() =>
                run(() => vacanciesApi.addCard(Number(addingToVacancy), cid), 'Добавлено в воронку')
              }
            >
              Добавить
            </Button>
          </Group>
        )}
      </Card>

      <Card withBorder>
        <Title order={5} mb="sm">Активности</Title>
        <Group mb="sm" align="flex-end">
          <TextInput
            label="Комментарий" placeholder="Текст комментария…" value={comment}
            onChange={(e) => setComment(e.currentTarget.value)} style={{ flex: 1 }}
          />
          <Button
            size="sm"
            disabled={!comment.trim()}
            onClick={() =>
              run(() => activitiesApi.comment(cid, comment.trim()), 'Комментарий добавлен').then(
                () => setComment('')
              )
            }
          >
            Отправить
          </Button>
        </Group>

        <Divider mb="sm" />
        <Group align="flex-end" mb="md">
          <TextInput
            label="Новая задача" placeholder="Что нужно сделать…" value={taskBody}
            onChange={(e) => setTaskBody(e.currentTarget.value)} style={{ flex: 1 }}
          />
          <TextInput
            label="Срок" type="datetime-local" value={taskDue}
            onChange={(e) => setTaskDue(e.currentTarget.value)} w={220}
          />
          <Button
            size="sm"
            disabled={!taskBody.trim()}
            onClick={() =>
              run(
                () =>
                  activitiesApi.createTask(
                    cid, taskBody.trim(),
                    taskDue ? new Date(taskDue).toISOString() : undefined
                  ),
                'Задача создана'
              ).then(() => { setTaskBody(''); setTaskDue(''); })
            }
          >
            Создать задачу
          </Button>
        </Group>

        <Table>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Тип</Table.Th>
              <Table.Th>Текст</Table.Th>
              <Table.Th>Срок</Table.Th>
              <Table.Th>Статус</Table.Th>
              <Table.Th>Дата</Table.Th>
              <Table.Th />
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {activities.map((a) => (
              <Table.Tr key={a.id}>
                <Table.Td>
                  <Badge variant="light" color={a.type === 'task' ? 'orange' : 'gray'}>
                    {a.type === 'task' ? 'Задача' : a.type === 'comment' ? 'Коммент' : 'Событие'}
                  </Badge>
                </Table.Td>
                <Table.Td>{a.body}</Table.Td>
                <Table.Td>
                  {a.due_at ? new Date(a.due_at).toLocaleString('ru-RU') : '—'}
                </Table.Td>
                <Table.Td>
                  {a.task_status === 'done' ? '✅ выполнена' : a.type === 'task' ? 'в работе' : '—'}
                </Table.Td>
                <Table.Td>{new Date(a.created_at).toLocaleString('ru-RU')}</Table.Td>
                <Table.Td>
                  {a.type === 'task' && a.task_status === 'open' && (
                    <Button size="compact-xs" onClick={() => completeTask(a)}>Выполнить</Button>
                  )}
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
        {activities.length === 0 && <Text c="dimmed" size="sm">Активностей пока нет</Text>}
      </Card>
    </Stack>
  );
}
