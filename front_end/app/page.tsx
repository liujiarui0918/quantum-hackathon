import { redirect } from 'next/navigation';

export default function Home() {
  redirect('/scenarios/unit-commitment/tasks');
}
