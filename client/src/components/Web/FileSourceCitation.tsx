import React, { useCallback } from 'react';
import { useRecoilValue } from 'recoil';
import * as Ariakit from '@ariakit/react';
import { VisuallyHidden } from '@ariakit/react';
import { ChevronDown, Paperclip } from 'lucide-react';
import { useToastContext } from '@librechat/client';
import { ExternalLinkDialog } from './ExternalLinkDialog';
import { useFileDownload } from '~/data-provider';
import { useLocalize } from '~/hooks';
import store from '~/store';

interface FileSourceCitationProps {
  source: any;
  label: string;
  citationId?: string;
  onMouseEnter?: () => void;
  onMouseLeave?: () => void;
}

export function FileSourceCitation({
  source,
  label,
  citationId,
  onMouseEnter,
  onMouseLeave,
}: FileSourceCitationProps) {
  const localize = useLocalize();
  const user = useRecoilValue(store.user);
  const { showToast } = useToastContext();

  const isLocalFile = source?.metadata?.storageType === 'local';
  const externalUrl = source?.metadata?.url;
  const hasExternalUrl = !!externalUrl;

  const { refetch: downloadFile } = useFileDownload(
    user?.id ?? '',
    !isLocalFile && !hasExternalUrl ? source.fileId : '',
  );

  const handleFileDownload = useCallback(
    async (e: React.MouseEvent) => {
      e.preventDefault();
      e.stopPropagation();

      if (!source?.fileId) return;

      if (isLocalFile) {
        showToast({
          status: 'error',
          message: localize('com_sources_download_local_unavailable'),
        });
        return;
      }

      try {
        const stream = await downloadFile();
        if (stream.data == null || stream.data === '') {
          showToast({
            status: 'error',
            message: localize('com_ui_download_error'),
          });
          return;
        }
        const link = document.createElement('a');
        link.href = stream.data;
        link.setAttribute('download', source.fileName || 'file');
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(stream.data);
      } catch (error) {
        showToast({
          status: 'error',
          message: localize('com_ui_download_error'),
        });
      }
    },
    [downloadFile, source, isLocalFile, localize, showToast],
  );

  const renderTrigger = () => {
    const buttonClass =
      'ml-1 inline-block h-5 max-w-36 cursor-pointer items-center overflow-hidden text-ellipsis whitespace-nowrap rounded-xl border border-border-heavy bg-surface-secondary px-2 text-xs font-medium text-blue-600 no-underline transition-colors hover:bg-surface-hover dark:border-border-medium dark:text-blue-400 dark:hover:bg-surface-tertiary';

    if (hasExternalUrl && externalUrl) {
      return (
        <ExternalLinkDialog
          url={externalUrl}
          trigger={
            <button className={buttonClass} onMouseEnter={onMouseEnter} onMouseLeave={onMouseLeave}>
              {label}
            </button>
          }
        />
      );
    }

    return (
      <button
        onClick={!isLocalFile ? handleFileDownload : undefined}
        className={buttonClass}
        onMouseEnter={onMouseEnter}
        onMouseLeave={onMouseLeave}
        title={isLocalFile ? localize('com_sources_download_local_unavailable') : undefined}
      >
        {label}
      </button>
    );
  };

  return (
    <span className="relative ml-0.5 inline-block">
      <Ariakit.HovercardProvider showTimeout={150} hideTimeout={150}>
        <span className="flex items-center">
          <Ariakit.HovercardAnchor render={renderTrigger()} />
          <Ariakit.HovercardDisclosure className="ml-0.5 rounded-full text-text-primary focus:outline-none focus:ring-2 focus:ring-ring">
            <VisuallyHidden>{localize('com_citation_more_details', { label })}</VisuallyHidden>
            <ChevronDown className="icon-sm" />
          </Ariakit.HovercardDisclosure>

          <Ariakit.Hovercard
            gutter={16}
            className="dark:shadow-lg-dark z-[999] w-[300px] max-w-[calc(100vw-2rem)] rounded-xl border border-border-medium bg-surface-secondary p-3 text-text-primary shadow-lg"
            portal={true}
            unmountOnHide={true}
          >
            <span className="mb-2 flex items-center">
              <div className="mr-2 flex h-4 w-4 items-center justify-center">
                <Paperclip className="h-3 w-3 text-text-secondary" />
              </div>
              <button
                onClick={!isLocalFile && !hasExternalUrl ? handleFileDownload : undefined}
                className="line-clamp-2 cursor-pointer overflow-hidden text-left text-sm font-bold text-[#0066cc] hover:underline dark:text-blue-400 md:line-clamp-3"
              >
                {source.attribution || source.title || localize('com_file_source')}
              </button>
            </span>

            {source.snippet && (
              <span className="my-2 text-ellipsis break-all text-xs text-text-secondary md:text-sm">
                {source.snippet}
              </span>
            )}

            <div className="mt-2 flex flex-wrap items-center gap-2">
              {source.metadata?.year && (
                <span className="rounded-md bg-surface-tertiary px-2 py-0.5 text-xs text-text-secondary">
                  {source.metadata.year}
                </span>
              )}
              {source.metadata?.contentsubtype && (
                <span className="rounded-md bg-surface-tertiary px-2 py-0.5 text-xs text-text-secondary">
                  {source.metadata.contentsubtype}
                </span>
              )}
            </div>
          </Ariakit.Hovercard>
        </span>
      </Ariakit.HovercardProvider>
    </span>
  );
}
