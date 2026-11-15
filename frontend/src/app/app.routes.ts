import { Routes } from '@angular/router';
import { ReadingQueue } from './features/reading-queue/reading-queue';

export const routes: Routes = [
  { path: '', component: ReadingQueue, title: 'Reading Queue — Lit Review' },
  { path: '**', redirectTo: '' },
];
