import { useEffect, useState } from 'react';
import {
  Badge, Card, Grid, Group, Loader, Progress, Stack, Table, Text, Title,
} from '@mantine/core';
import { dashboardApi, activitiesApi } from '../api/endpoints';
import { STAGES } from '../api/types';
import type { Activity, DashboardData } from '../api/types';
import { useAuth } from '../hooks/useAuth';

const stageLabel = (value: string) => STAGES.find((s) => s.value === value)?.label ?? value;

export default function DashboardPage() {
  const { user } = useAuth();
  const [data, setData] = useState<DashboardData | null>(null);
  const [tasks, setTasks] = useState<Activity[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([dashboardApi.get(), activitiesApi.today()])
      .then(([d, t]) => {
        setData(d);
        setTasks(t);
      })
      .catch((e) => setError(e.message));
  }, []);

  if (error) return <Text c="red">{error}</Text>;
  if (!data) return <Loader />;

  const maxStage = Math.max(...data.stages.map((s) => s.count), 1);

  return (
    <Stack>
      <Title order={2}>Дашборд</Title>

      <Grid>
        <Grid.Col span={{ base: 12, sm: 3 }}>
          <Card withBorder>
            <Text c="dimmed" size="sm">Кандидатов всего</Text>
            <Title order={3}>{data.total_candidates}</Title>
          </Card>
        </Grid.Col>
        <Grid.Col span={{ base: 12, sm: 3 }}>
          <Card withBorder>
            <Text c="dimmed" size="sm">Открытых вакансий</Text>
            <Title order={3}>{data.open_vacancies}</Title>
          </Card>
        </Grid.Col>
        <Grid.Col span={{ base: 12, sm: 3 }}>
          <Card withBorder>
            <Text c="dimmed" size="sm">Задач на сегодня</Text>
            <Title order={3} c={data.tasks_today > 0 ? 'orange.8' : undefined}>
              {data.tasks_today}
            </Title>
          </Card>
        </Grid.Col>
        <Grid.Col span={{ base: 12, sm: 3 }}>
          <Card withBorder>
            <Text c="dimmed" size="sm">Моя роль</Text>
            <Title order={4}>{user?.role === 'admin' ? 'Администратор' : 'Рекрутер'}</Title>
          </Card>
        </Grid.Col>
      </Grid>

      <Grid>
        <Grid.Col span={{ base: 12, md: 6 }}>
          <Card withBorder>
            <Title order={5} mb="sm">Кандидаты по стадиям</Title>
            <Stack gap="xs">
              {data.stages.map((s) => (
                <Group key={s.stage} justify="space-between">
                  <Text size="sm" w={220}>{stageLabel(s.stage)}</Text>
                  <Progress value={(s.count / maxStage) * 100} w="60%" size="sm" />
                  <Text size="sm" fw={600} w={30} ta="right">{s.count}</Text>
                </Group>
              ))}
            </Stack>
          </Card>
        </Grid.Col>

        <Grid.Col span={{ base: 12, md: 6 }}>
          <Card withBorder mb="md">
            <Title order={5} mb="sm">Задачи на сегодня (просроченные в том числе)</Title>
            {tasks.length === 0 ? (
              <Text c="dimmed" size="sm">Задач нет</Text>
            ) : (
              <Stack gap={4}>
                {tasks.map((t) => (
                  <Group key={t.id} justify="space-between">
                    <Text size="sm">{t.body}</Text>
                    <Badge color="orange" variant="light">
                      {t.due_at ? new Date(t.due_at).toLocaleString('ru-RU') : ''}
                    </Badge>
                  </Group>
                ))}
              </Stack>
            )}
          </Card>

          <Card withBorder>
            <Title order={5} mb="sm">Статистика по рекрутерам</Title>
            <Table striped>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Рекрутер</Table.Th>
                  <Table.Th ta="right">Кандидатов</Table.Th>
                  <Table.Th ta="right">Принято</Table.Th>
                  <Table.Th ta="right">Отказов</Table.Th>
                  <Table.Th ta="right">Вакансий</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {data.recruiter_stats.map((r) => (
                  <Table.Tr key={r.user_id}>
                    <Table.Td>{r.full_name}</Table.Td>
                    <Table.Td ta="right">{r.candidates}</Table.Td>
                    <Table.Td ta="right">{r.hired}</Table.Td>
                    <Table.Td ta="right">{r.rejected}</Table.Td>
                    <Table.Td ta="right">{r.open_vacancies}</Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </Card>
        </Grid.Col>
      </Grid>
    </Stack>
  );
}
