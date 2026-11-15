import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import {
  AnalyzePaperResult,
  BonusUpdateResponse,
  CollectionItem,
  HealthStatus,
  PaperDetailResponse,
  PaperSummary,
  StatusUpdateResponse,
  SyncAllResponse,
  SyncPaperResult,
  TagUpdateResponse,
} from '../models/paper.model';

@Injectable({ providedIn: 'root' })
export class ApiClient {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = 'http://localhost:8000/api';

  getHealth(): Observable<HealthStatus> {
    return this.http.get<HealthStatus>(`${this.baseUrl}/health`);
  }

  getCollections(): Observable<CollectionItem[]> {
    return this.http.get<CollectionItem[]>(`${this.baseUrl}/papers/collections`);
  }

  getPapers(filters?: {
    collectionKey?: string;
    tag?: string;
    status?: string;
    limit?: number;
  }): Observable<PaperSummary[]> {
    let params = new HttpParams().set('limit', String(filters?.limit ?? 200));
    if (filters?.collectionKey) {
      params = params.set('collection_key', filters.collectionKey);
    }
    if (filters?.tag) {
      params = params.set('tag', filters.tag);
    }
    if (filters?.status) {
      params = params.set('status', filters.status);
    }
    return this.http.get<PaperSummary[]>(`${this.baseUrl}/papers`, { params });
  }

  updateManualBonus(citekey: string, manualBonus: number): Observable<BonusUpdateResponse> {
    return this.http.patch<BonusUpdateResponse>(`${this.baseUrl}/papers/${citekey}/bonus`, {
      manual_bonus: manualBonus,
    });
  }

  updatePaperStatus(citekey: string, status: 'read' | 'unread'): Observable<StatusUpdateResponse> {
    return this.http.patch<StatusUpdateResponse>(`${this.baseUrl}/papers/${citekey}/status`, {
      status,
    });
  }

  syncAll(forceFull = false): Observable<SyncAllResponse> {
    return this.http.post<SyncAllResponse>(`${this.baseUrl}/sync`, null, {
      params: new HttpParams().set('force_full', String(forceFull)),
    });
  }

  getPaperDetail(citekey: string): Observable<PaperDetailResponse> {
    return this.http.get<PaperDetailResponse>(`${this.baseUrl}/papers/${citekey}`);
  }

  addTags(itemKey: string, tags: string[]): Observable<TagUpdateResponse> {
    return this.http.post<TagUpdateResponse>(`${this.baseUrl}/papers/${itemKey}/tags`, { tags });
  }

  syncPaper(itemKey: string, force = false): Observable<SyncPaperResult> {
    return this.http.post<SyncPaperResult>(`${this.baseUrl}/sync/${itemKey}`, null, {
      params: new HttpParams().set('force', String(force)),
    });
  }

  analyzePaper(itemKey: string, force = false): Observable<AnalyzePaperResult> {
    return this.http.post<AnalyzePaperResult>(`${this.baseUrl}/sync/${itemKey}/analyze`, null, {
      params: new HttpParams().set('force', String(force)),
    });
  }
}
