import { Routes } from '@angular/router';
import { PaperDetail } from './features/paper-detail/paper-detail';
import { ReadingQueue } from './features/reading-queue/reading-queue';

export const routes: Routes = [
  { path: '', component: ReadingQueue, title: 'Reading Queue — Lit Review' },
  { path: 'papers/:citekey', component: PaperDetail, title: 'Paper Detail — Lit Review' },
  { path: '**', redirectTo: '' },
];
