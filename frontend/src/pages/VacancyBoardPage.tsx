import { useCallback, useEffect, useState } from 'react';
import {
  Button, Card, Group, Loader, Modal, Select, Stack, Text, Textarea, Title,
} from '@mantine/core';
import { IconArrowLeft } from '@tabler/icons-react';
import { useNavigate, useParams } from 'react-router-dom';
import { notifications } from '@mantine/notifications';
import { candidatesApi, vacanciesApi } from '../api/endpoints';
import type { Card as KanbanCard, Vacancy } from '../api/types';
import { STAGES } from '../api/types';

/** Kanban board with native HTML5 drag & drop. */
export default function VacancyBoardPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const vacancyId = Number(id);
  const [vacancy, setVacancy] = useState<Vacancy | null>(null);
  const [board, setBoard] = useState<Record<string, KanbanCard[]>>({});
  const [loading, setLoading] = useState(true);
  const [dragCard, setDragCard] = useState<KanbanCard | null>(null);
  const [candidateId, setCandidateId] = useState<string | null>(null);
  const [candidateOptions, setCandidateOptions] = useState<{ value: string; label: string }[]>([]);
  const [rejectCard, setRejectCard] = useState<KanbanCard | null>(null);
  const [rejectReason, setRejectReason] = useState('');
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    Promise.all([vacanciesApi.get(vacancyId), vacanciesApi.board(vacancyId)])
      .then(([v, b]) => {
        setVacancy(v);
        setBoard(b.stages);
      })
      .catch((e) => notifications.show({ color: 'red', message: e.message }))
      .finally(() => setLoading(false));
  }, [vacancyId]);

  useEffect(load, [load]);

  useEffect(() => {
    candidatesApi
      .list({ page_size: 100 })
      .then((p) =>
        setCandidateOptions(
          p.items.map((c) => ({
            value: String(c.id),
            label: `${c.full_name}${c.position ? ` — ${c.position}` : ''}`,
          }))
        )
      )
      .catch(() => {});
  }, []);

  const onDrop = async (stage: string) => {
    const card = dragCard;
    setDragCard(null);
    if (!card || card.stage === stage) return;

    if (stage === 'rejected') {
      setRejectCard(card);
      setRejectReason('');
      return;
    }
    // optimistic update
    const prev = board;
    const next: Record<string, KanbanCard[]> = {};
    Object.entries(board).forEach(([k, cards]) => {
      next[k] = cards.filter((c) => c.id !== card.id);
    });
    next[stage] = [...(next[stage] ?? []), { ...card, stage }];
    setBoard(next);
    try {
      await vacanciesApi.moveCard(card.id, stage);
      load();
    } catch (e) {
      setBoard(prev);
      notifications.show({ color: 'red', message: e instanceof Error ? e.message : 'Ошибка' });
    }
  };

  const confirmReject = async () => {
    if (!rejectCard || !rejectReason.trim()) return;
    setBusy(true);
    try {
      await vacanciesApi.moveCard(rejectCard.id, 'rejected', { reject_reason: rejectReason.trim() });
      notifications.show({ color: 'green', message: 'Карточка переведена в «Отказ»' });
      setRejectCard(null);
      load();
    } catch (e) {
      notifications.show({ color: 'red', message: e instanceof Error ? e.message : 'Ошибка' });
    } finally {
      setBusy(false);
    }
  };

  const addCandidate = async () => {
    if (!candidateId) return;
    try {
      await vacanciesApi.addCard(vacancyId, Number(candidateId));
      notifications.show({ color: 'green', message: 'Кандидат добавлен в воронку' });
      setCandidateId(null);
      load();
    } catch (e) {
      notifications.show({ color: 'red', message: e instanceof Error ? e.message : 'Ошибка' });
    }
  };

  if (loading) return <Loader />;
  if (!vacancy) return <Text c="red">Вакансия не найдена</Text>;

  return (
    <Stack>
      <Group justify="space-between">
        <div>
          <Button
            variant="subtle" size="sm" leftSection={<IconArrowLeft size={14} />}
            onClick={() => navigate('/vacancies')} mb={4}
          >
            Все вакансии
          </Button>
          <Title order={2}>{vacancy.title}</Title>
          <Text c="dimmed" size="sm">
            {[vacancy.client,
              vacancy.salary_min && vacancy.salary_max
                ? `${vacancy.salary_min.toLocaleString('ru-RU')} – ${vacancy.salary_max.toLocaleString('ru-RU')}`
                : null,
            ].filter(Boolean).join(' · ')}
          </Text>
        </div>
        <Group align="flex-end">
          <Select
            placeholder="Добавить кандидата" searchable clearable w={280}
            data={candidateOptions} value={candidateId} onChange={setCandidateId}
          />
          <Button onClick={addCandidate} disabled={!candidateId}>Добавить</Button>
        </Group>
      </Group>

      <div
        style={{
          display: 'flex', gap: 12, overflowX: 'auto', paddingBottom: 12,
          alignItems: 'flex-start',
        }}
      >
        {STAGES.map(({ value, label }) => {
          const cards = board[value] ?? [];
          return (
            <div
              key={value}
              data-testid={`column-${value}`}
              onDragOver={(e) => e.preventDefault()}
              onDrop={() => onDrop(value)}
              style={{
                minWidth: 250, width: 250, background: '#f8f9fa',
                borderRadius: 8, padding: 10, minHeight: 180,
                border: dragCard ? '2px dashed #ced4da' : '2px solid transparent',
              }}
            >
              <Group justify="space-between" mb={8}>
                <Text size="sm" fw={600}>{label}</Text>
                <Text size="xs" c="dimmed">{cards.length}</Text>
              </Group>
              <Stack gap={8}>
                {cards.map((card) => (
                  <Card
                    key={card.id}
                    withBorder
                    padding="sm"
                    draggable
                    onDragStart={() => setDragCard(card)}
                    onDragEnd={() => setDragCard(null)}
                    style={{ cursor: 'grab', opacity: dragCard?.id === card.id ? 0.5 : 1 }}
                  >
                    <Text
                      size="sm" fw={600}
                      style={{ cursor: 'pointer' }}
                      onClick={() => navigate(`/candidates/${card.candidate_id}`)}
                    >
                      {card.candidate?.full_name ?? `#${card.candidate_id}`}
                    </Text>
                    <Text size="xs" c="dimmed">{card.candidate?.position}</Text>
                    {card.stage === 'rejected' && card.reject_reason && (
                      <Text size="xs" c="red.7" mt={4}>{card.reject_reason}</Text>
                    )}
                    <Text size="xs" c="dimmed" mt={4}>
                      стадий: {card.history?.length ?? 0}
                    </Text>
                  </Card>
                ))}
                {cards.length === 0 && (
                  <Text size="xs" c="dimmed" ta="center" py={8}>Перетащите сюда</Text>
                )}
              </Stack>
            </div>
          );
        })}
      </div>

      <Modal
        opened={!!rejectCard}
        onClose={() => setRejectCard(null)}
        title="Причина отказа (обязательно)"
      >
        <Stack>
          <Textarea
            placeholder="Например: не готов к офлайну, уровень ниже junior…"
            value={rejectReason}
            onChange={(e) => setRejectReason(e.currentTarget.value)}
            rows={3}
          />
          <Button
            color="red" loading={busy}
            disabled={!rejectReason.trim()} onClick={confirmReject}
          >
            Подтвердить отказ
          </Button>
        </Stack>
      </Modal>
    </Stack>
  );
}
